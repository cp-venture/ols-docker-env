<?php
echo rand();
//print_r($args);
//echo $args[0];
echo $args[0];
$_POST=$args[0];
do_action('wp_ajax_updraft_importsettings')

?>
