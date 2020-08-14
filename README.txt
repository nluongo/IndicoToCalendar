This is intended to solve the problem of emails with indico links needed to be downloaded and then imported into Google Calendar individually. This is annoying.
Currently the script will find all emails in the local CalendarImport folder, extract the indico url present in the message body, and download the ics file at that url.

Steps necessary to make this thing work:
1. Move the email whose event you would like to download to the local folder name "CalendarImport"
2. Run the script
