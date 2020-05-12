import boto3
import git
import subprocess
import json
import docker
import os
import time
from getpass import getpass
import subprocess

project_dir = os.path.dirname(os.path.abspath(__file__))
# os.environ['GIT_ASKPASS'] = os.path.join(project_dir, 'askpass.py')


BUCKET_NAME = 'cp-backup-s3bucket'
BACKUP_DIR_NAME = '.Backups'
TEMP_DIR_NAME = '.temp'
OLS_CONTAINER_NAME = 'ols-docker-env_litespeed_1'
WP_PATH_REL = 'localhost/html'
DOCKER_MAPPED_WP_PATH = None

s3 = boto3.client('s3')
response = s3.list_buckets()

# Output the bucket names
print('Existing buckets:')
for bucket in response['Buckets']:
    print(f'  {bucket["Name"]}')



####################################
client = docker.from_env()
c_ins = client.containers.get(OLS_CONTAINER_NAME)
cwd = c_ins.exec_run('sh -c "echo $PWD"')
DOCKER_MAPPED_WP_PATH = os.path.join(str(cwd[1])[2:-3], WP_PATH_REL)
####################################
print(DOCKER_MAPPED_WP_PATH)

from git import Repo, repo
repo_plugins = Repo(os.path.join('sites/',WP_PATH_REL, 'wp-content', 'plugins'))
repo_theme = Repo(os.path.join('sites/',WP_PATH_REL, 'wp-content', 'themes', 'main'))
repo_base = Repo(os.getcwd())


def run(*args):
    return subprocess.check_call(['git'] + list(args))

subprocess.call('ssh-add ./githu_key', shell=True)
subprocess.Popen(['git', 'config', '--global', 'user.email', '"wittycodes@gmail.com"'])
subprocess.Popen(['git', 'config', '--global', 'user.password', '"aha@9857"'])

import requests
requests.get('https://api.github.com/notifications', auth=("wittycodes", "55c3eb8c69f032326dcb59a756397b38ea2a979b"))

def configure(repo):
    w = repo.config_writer()
    w.set_value("user", "name", "wittycodes").release()
    w.set_value("user", "email", "wittycodes@gmail.com").release()
    w.set_value("user", "password", "aha@9857").release()
    print(repo.config_reader().read())

configure(repo_theme)
configure(repo_plugins)
configure(repo_base)

def get_hash(repo):
    sha = repo.commit('master')
    return repo.git.rev_parse(sha, short=5)

def push_tag(repo, tag):
    repo.git.add(A=True)
    try:
        print(repo.git.commit("-m", f"auto commit for tag:{tag}"))
        repo.remote().push()
    except:
        pass
    try:
        repo.create_tag(tag, message=f"checkpoint reached addressed by tag:{tag}")
    except:
        pass
    print(repo.git.push('--tags'))

def push_changes(tag):
    push_tag(repo_plugins, tag)
    push_tag(repo_theme, tag)
#
# repo_theme

def pull_tag(repo, tag, revert):
    repo.git.stash()
    if revert:
        repo.git.reset('--hard', str(tag))
    else:
        v = (repo.git.branch('-r')).split('\n')
        print(v)
        v = [i.strip() for i in v]
        print(v)
        l = []
        a = ''
        for i in v:
            if i.startswith(f'origin/{tag}'):
                try:
                    l.append(int(a.split('.')[-1]))
                except:
                    pass
        if len(l) != 0:
            mx = max(l)
        else:
            mx = -1
        repo.git.checkout(f'tags/{tag}', "-b", f'{tag}.{mx+1}')
        repo.git.pull()
    repo.git.push('--force')


def pull_changes(tag, revert):
    pull_tag(repo_plugins, tag)
    pull_tag(repo_theme, tag)

# import uuid
# print(uuid.uuid4())
# control_content = {
#     'control_data':{
#         '750f785f-ff26-40c5-bf22-7442cd797a95':{
#             'theme_commit_id': "ead45d",
#             'plugins_commit_id': "34ced2",
#             'timestamp': 2342341123
#         },
#         'eabc9845-6c42-476d-bc6d-7e2cf7c3231c':{
#             'theme_commit_id': "1ad45d",
#             'plugins_commit_id': "8dc4d2",
#             'timestamp': 2342341452
#         }
#     }
# }
#
# import pandas as pd
# df=pd.read_json(json.dumps(control_content['control_data']), orient='index')
# print(df)

def set_sql_filename(tag):
    sql_backup_filename = 'TS-{TS}.TAG-{TAG}.sql'
    ts = time.time()
    h = sql_backup_filename.format( TS=str(round(ts)).lower(), TAG=str(tag).lower().replace('.', '_'))
    print(h)
    return h

def get_sql_filename(filename):
    h = filename[:-4].split('.')
    print(h)
    meta = {}
    for i in h:
        j = i.split('-')
        meta[j[0]]= str(j[1]).lower()
    print(json.dumps(meta, indent=4))



def export_db(filename):
    client = docker.from_env()
    c_ins = client.containers.get(OLS_CONTAINER_NAME)
    cwd = c_ins.exec_run('sh -c "echo $PWD"')
    cmd = '''
    mkdir {backup_dir}
    cd {WP_PATH_REL}
    wp db export ../../{backup_dir}/{file_name} --allow-root
    '''.format(WP_PATH_REL=WP_PATH_REL,backup_dir=BACKUP_DIR_NAME, file_name=filename)
    print(c_ins.exec_run('bash -c "{cmd}"'.format(cmd=cmd)))
    return os.path.join('sites', BACKUP_DIR_NAME, filename)

def import_db(file_path):
    client = docker.from_env()
    c_ins = client.containers.get(OLS_CONTAINER_NAME)
    cmd = '''
    cd {WP_PATH_REL}
    wp db import {file_path} --allow-root
    '''.format(WP_PATH_REL=WP_PATH_REL,file_path=file_path)
    print(c_ins.exec_run('bash -c "{cmd}"'.format(cmd=cmd)))


def s3_upload(file_path, key):
    s3.upload_file(
        Filename=file_path, Bucket=BUCKET_NAME, Key=key
    )
    print(s3.list_objects(Bucket=BUCKET_NAME))

def s3_download(key):
    temp_path = os.path.join('sites', TEMP_DIR_NAME)
    file_path = os.path.join(temp_path, key)

    print(file_path)
    try:
        os.mkdir(temp_path)

    except:
        pass
    print(temp_path)
    s3.download_file(
        Filename=file_path, Key=key, Bucket=BUCKET_NAME
    )
    print('ninioooooooooo')
    return os.path.join('../..', TEMP_DIR_NAME, key)


# subprocess.call("ls -lha", shell=True, cwd='../../sites/localhost/html')

######### For Backup #########
# tag = "12"
#
# push_changes(tag)
# a = set_sql_filename(tag)
# fp = export_db(filename=a)
# s3_upload(file_path=fp, key=a)
#
#
#
# ########## For Restore ########
# tag = "12"
#
# pull_changes(tag)
# fp = s3_download(key=b)
# import_db(file_path=fp)
# get_sql_filename(a)

"""
wp backup database export sql file

- Branch backups
- Branch 

"""
push_changes('v1')

