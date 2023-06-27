<!-- ?end=230623&len=5-->

<head>
<meta charset="UTF-8" />
<title>我的某群組 line 聊天紀錄</title>
<link type="text/css" rel="stylesheet" title="user-defined Style" href="linespector.css" />
</head>

<body>

<h1>我的某 line 群組聊天紀錄</h1>

<?php
include "config.php";
# echo "$DB_PATH";
parse_str($_SERVER['QUERY_STRING'], $ARGS);
if (array_key_exists('end', $ARGS) &&  preg_match('/^(\d\d)(\d\d)(\d\d)/', $ARGS['end'], $matches)) {
    $final_date = new DateTimeImmutable("20$matches[1]-$matches[2]-$matches[3]");
} else {
    $final_date = new DateTimeImmutable();
}
if (array_key_exists('len', $ARGS)) {
    if ($ARGS['len']>=31) $ARGS['len'] = 31;
} else {
    $ARGS['len'] = 7;
}
$begin_date = $final_date->modify("-{$ARGS['len']} days");
$day0 = $begin_date->format('Y-m-d');
$day9 = $final_date->format('Y-m-d');
echo "<h2>[$day0 => $day9]</h2>";

$db = new SQLite3($DB_PATH);
$res = $db->query("select * from messages_with_images where date(time_stamp, 'unixepoch')>='$day0' and date(time_stamp, 'unixepoch')<='$day9'");
echo "<ul>\n";
while ($row = $res->fetchArray()) {
    $date = date('m-d', $row['time_stamp']);
    $time = date('H:i', $row['time_stamp']);
    $img = $row['img_content'];
    if (strlen($img) > 0) {
	$img = sprintf(
	    '<img src="data:image/jpg;base64,%s" />',
	    base64_encode($img)
	);
	$row['msg_content'] = '';
    } elseif ($row['msg_type'] == '貼圖') {
	$img = sprintf('<img src="%s" />', $row['msg_content']);
	$row['msg_content'] = '';
    }
    echo "<li>$date $time {$row['msg_type']} {$row['user_name']}<br />\n{$row['msg_content']}<br />\n$img\n";
}
echo "</ul>\n";
?>

</body>
