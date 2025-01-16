import base64
import mimetypes
import os
import pickle
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import google.auth.transport.requests
import google_auth_oauthlib.flow
import googleapiclient.discovery

from util.config import MESSAGES, ROOT_PATH
from util.set import sets


def gmail_authenticate():

    creds = None
    # the file gmail_token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time
    if os.path.exists(f"{ROOT_PATH}/files/gmail_token.pickle"):
        with open(f"{ROOT_PATH}/files/gmail_token.pickle", "rb") as token:
            creds = pickle.load(token)
    # if there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(google.auth.transport.requests.Request())
        else:
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                f"{ROOT_PATH}/files/gmail.json", scopes=["https://mail.google.com/"]
            )
            creds = flow.run_local_server(port=0)
        # save the credentials for the next run
        with open(f"{ROOT_PATH}/files/gmail_token.pickle", "wb") as token:
            pickle.dump(creds, token)
    return googleapiclient.discovery.build("gmail", "v1", credentials=creds)


# Adds the attachment with the given filename to the given message
def add_attachment(message, filename):
    content_type, encoding = mimetypes.guess_type(filename)
    if not content_type or encoding:
        content_type = "application/octet-stream"
    main_type, sub_type = content_type.split("/", 1)
    if main_type == "text":
        fp = open(filename, "rb")
        message_attachment = MIMEText(fp.read().decode(), _subtype=sub_type)
        fp.close()
    elif main_type == "image":
        fp = open(filename, "rb")
        message_attachment = MIMEImage(fp.read(), _subtype=sub_type)
        fp.close()
    elif main_type == "audio":
        fp = open(filename, "rb")
        message_attachment = MIMEAudio(fp.read(), _subtype=sub_type)
        fp.close()
    else:
        fp = open(filename, "rb")
        message_attachment = MIMEBase(main_type, sub_type)
        message_attachment.set_payload(fp.read())
        fp.close()
    filename = os.path.basename(filename)
    message_attachment.add_header(
        "Content-Disposition", "attachment", filename=filename
    )
    message.attach(message_attachment)


def build_message(our_email, destination, obj, body, attachments=None):
    if attachments is None:
        attachments = []
    if not attachments:  # no attachments given
        message = MIMEText(body)
        message["to"] = destination
        message["from"] = our_email
        message["subject"] = obj
    else:
        message = MIMEMultipart()
        message["to"] = destination
        message["from"] = our_email
        message["subject"] = obj
        message.attach(MIMEText(body))
        for filename in attachments:
            add_attachment(message, filename)
    return {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode()}


def search_messages(serv, search_text):
    result = serv.users().messages().list(userId="me", q=search_text).execute()
    messages = []
    if "messages" in result:
        messages.extend(result["messages"])
    while "nextPageToken" in result:
        page_token = result["nextPageToken"]
        result = (
            serv.users()
            .messages()
            .list(userId="me", q=search_text, pageToken=page_token)
            .execute()
        )
        if "messages" in result:
            messages.extend(result["messages"])
    return messages


def clean(text):
    # clean text for creating a folder
    return "".join(c if c.isalnum() else "_" for c in text)


def parse_parts(serv, parts, message, email_content):
    """
    Utility function that parses the content of an email partition
    """

    if parts:
        for part in parts:
            mimetype = part.get("mimeType")
            body = part.get("body")
            data = body.get("data")
            if part.get("parts"):
                # recursively call this function when we see that a part
                # has parts inside
                parse_parts(serv, part.get("parts"), message, email_content)
            if mimetype == "text/plain":
                # if the email part is text plain
                if data:
                    text = base64.urlsafe_b64decode(data).decode()
                    email_content.append(("text", text))
                    # filename = "text.txt"
                    # filepath = path.join(folder_name, filename)
                    # with open(filepath, "w", encoding='utf-8') as f:
                    #     f.write(text)
            elif mimetype == "text/html":
                pass
            else:
                pass


class Email:

    def read(self):
        result = (
            "From: "
            + self.e_from
            + "\nTo: "
            + self.e_to
            + "\nSubject: "
            + self.subject
            + "\nDate: "
            + self.date
        )
        for value in self.content:
            result = result + "\n" + value[0] + ": " + value[1]
        return result

    e_from = ""
    e_to = ""
    subject = ""
    folder_name = "no_subject"
    date = ""
    content = []


def read_message(serv, message):
    """
    This function takes Gmail API `service` and the given `message_id` and does the following:
        - Downloads the content of the email
        - Prints email basic information (To, From, Subject & Date) and plain/text parts
        - Creates a folder for each email based on the subject
        - Downloads text/html content (if available) and saves it under the folder created as index.html
        - Downloads any file that is attached to the email and saves it in the folder created
    """
    message_r = (
        serv.users()
        .messages()
        .get(userId="me", id=message["id"], format="full")
        .execute()
    )
    # parts can be the message body, or attachments
    payload = message_r["payload"]
    headers = payload.get("headers")
    text = message_r["snippet"]
    parts = payload.get("parts")

    the_email = Email()
    if headers:
        for header in headers:
            name = header.get("name")
            value = header.get("value")
            if name.lower() == "from":
                the_email.e_from = value
            if name.lower() == "to":
                the_email.e_to = value
            if name.lower() == "subject":
                the_email.subject = value
                the_email.folder_name = clean(value)
            if name.lower() == "date":
                the_email.date = value.split(", ")[1]

    parse_parts(serv, parts, message, the_email.content)
    if (len(the_email.content) == 0) and (text != ""):
        the_email.content.append(("text", text))
    return the_email


# get the Gmail API service
service = gmail_authenticate()


def email_get():
    emails = search_messages(service, search_text="in:inbox")
    if len(emails) == 0:
        return "None"
    else:
        service.users().messages().modify(
            userId="me", id=emails[-1]["id"], body={"removeLabelIds": ["INBOX"]}
        ).execute()
        email_content = read_message(service, emails[-1]).read()
        return email_content


def email_send(param):
    e_to = param[0]
    e_subject = param[1]
    e_text = param[2]
    if len(param) > 3:
        e_attachments = param[3]
    else:
        e_attachments = None
    # e_attachments = ["test.py", "files/screenshot.png"]
    e_from = "tennisbot0@gmail.com"
    if e_attachments:
        e_attachments = e_attachments.split(";")
    body = build_message(e_from, e_to, e_subject, e_text, e_attachments)
    service.users().messages().send(userId="me", body=body).execute()
    return MESSAGES.get(sets.lang, {}).get("email_send_success", '')
