import boto3
import git
import subprocess
import json
import docker
import os

BUCKET_NAME = 'cp-backup-s3bucket'
BACKUP_DIR_NAME = '.Backups'
TEMP_DIR_NAME = '.temp'
OLS_CONTAINER_NAME = 'olsdockerenv_litespeed_1'
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

def get_hash(repo):
    sha = repo.commit('master')
    return repo.git.rev_parse(sha, short=5)
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

def set_sql_filename(timestamp=2242341123 ,theme_commit='ead45d', plugins_commit='34ced2', tagged=False):
    sql_backup_filename = 'TM-{TM}_PG-{PG}.sql'
    h = sql_backup_filename.format( TM=str(get_hash(repo_theme)).lower(), PG=str(get_hash(repo_plugins)).lower())
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

a = set_sql_filename(plugins_commit=repo_plugins, theme_commit=repo_theme)
fp = export_db(filename=a)
s3_upload(file_path=fp, key=a)



b = a
fp = s3_download(key=b)
import_db(file_path=fp)


get_sql_filename(a)

"""
wp backup database export sql file

- Branch backups
- Branch 

"""
