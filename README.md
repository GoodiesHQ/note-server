# note-server

A simple server, API, and DOA to store notes.

As of now, only postgresql databases are supported, but is very easily extensible via the `BaseNoteDOA` class. The server runs on [Sanic](https://github.com/channelcat/sanic), and therefore requires Python 3.5.0 or newer.

### Database
Database table should have the following design:

Name|Type|Attributes|Description
----|----|----------|-----------
id|SERIAL INTEGER|Primary Key|Auto-incrementing index for notes
uid|TEXT|NOT NULL|A 21-character unique ID for the note
title|TEXT|NOT NULL|The title of the note
note|TEXT|NOT NULL|The content of the note
created|TIMESTAMP|NOT NULL|Timestamp of note creation
expires|TIMESTAMP||Timestamp of note expiration (or NULL if volatile/single-use)

If encryption is desired, consider using the [Note-WebApp](https://github.com/GoodiesHQ/note-webapp) I've created which performs client-side encryption/decryption and prevents passwords from being sent over HTTP.

### Web API:

URL|Methods|Parameter(s)|Return Type|Return Value
---|-------|------------|-----------|------------
/api/create|POST|uid(str) - Note UID|JSON| {<br>"success": Boolean,<br>"message": String,<br>\/\*If success === true:\*\/<br>"title": String,<br>"note": String<br>}
/api/get|POST|uid(str) - Note UID|JSON| {<br>"success": Boolean,<br>"message": String,<br>\/\*If success === true:\*\/<br>"uid": String<br>}

The Sanic application will seve everything in the `dist` folder as `/`.
