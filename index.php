<!-- ?end=230623&len=5-->

<?php include "config.php"; ?>

<head>
<meta charset="UTF-8" />
<title>我的 line 群組聊天紀錄： 「<?= $CHAT_TITLE ?>」</title>
<link type="text/css" rel="stylesheet" title="user-defined Style" href="linespector.css" />
</head>

<body>

<h1>我的 line 群組聊天紀錄： 「<?= $CHAT_TITLE ?>」</h1>

<?php
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
$N = $ARGS['len'];
$begin_date = $final_date->modify("-$N days");
$day0 = $begin_date->format('Y-m-d');
$day9 = $final_date->format('Y-m-d');
$qs_prev = $begin_date->modify("-1 days")->format('ymd');
$qs_prev = "end=$qs_prev&len=$N";
$k = $N+1;
$qs_next = $final_date->modify("+$k days")->format('ymd');
$qs_next = "end=$qs_next&len=$N";
$navigator = <<<END
<div class='navigator'>
<div class='left'><a href="?$qs_prev">較舊</a></div>
<div class='right'><a href="?$qs_next">較新</a></div>
<div class='middle'>[$day0 =&gt; $day9]</div>
</div>
END;
echo "$navigator";

$db = new SQLite3($DB_PATH, SQLITE3_OPEN_READONLY);
# see https://www.sqlite.org/c3ref/open.html for SQLITE3_OPEN_READONLY
$res = $db->query("select * from messages_with_images where chat_title='$CHAT_TITLE' and date(time_stamp, 'unixepoch')>='$day0' and date(time_stamp, 'unixepoch')<='$day9'");
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

echo <<<END
$navigator
<p class="right"><a href="https://github.com/ckhung/linespector">linespector@github</a>
by <a href="https://ckhung0.blogspot.com/">資訊.人權.貴</a>
END;
?>

</body>
