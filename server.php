<?php
require_once(dirname(__file__) . "/bootstrap.php");

// http://stackoverflow.com/questions/3220547/websocket-handshake-problem/3237394#3237394

?>

<html>
<script src="http://ajax.googleapis.com/ajax/libs/jquery/1.4.3/jquery.min.js"></script>
<script>
if (window["WebSocket"]) {
    conn = new WebSocket("ws://heroesofconquest.se:8080/");
    conn.onopen = function(evt) {
		console.log('readystate:' + conn.readyState);
        console.log("connection open");
		conn.send('skickar meddelande');
    }
	conn.onclose = function(evt) {
		console.log('readystate:' + conn.readyState);
        console.log("connection closed");
    }
    conn.onmessage = function(evt) {
		console.log('readystate:' + conn.readyState);
		console.log('message');
        console.log(evt.data);
    }
	conn.onerror = function(error) {
	console.log('readystate:' + conn.readyState);
		console.log('error');
        console.log(error);
    }
	console.log('readystate:' + conn.readyState);
    if(!conn) {
        console.log("Failed to connect to server");
	}
}
</script>
</html>
   
