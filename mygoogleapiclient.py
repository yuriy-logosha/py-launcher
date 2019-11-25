#!/usr/bin/env python3
from __future__ import print_function
import googleapiclient
import os, io, http, datetime, time, subprocess, socket, sys
from oauth2client import file, client, tools
from apiclient import errors
from apiclient.discovery import build
from httplib2 import Http
from googleapiclient.errors import HttpError
from ssl import SSLError

SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly', 'https://www.googleapis.com/auth/spreadsheets']


def metadata():
    store = file.Storage('credentials.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('client_secret.json', SCOPES)
        creds = tools.run_flow(flow, store)
    return build('drive', 'v3', http=creds.authorize(Http()))

def sheets():
    store = file.Storage('credentials.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('client_secret.json', SCOPES)
        creds = tools.run_flow(flow, store)
    return build('sheets', 'v4', http=creds.authorize(Http()))

def getFileIdBy(name):
    pass

def getValues(fileId):
    try:
        return sheet(sheets(), fileId, "Form responses 1!A:Z")
    except (RuntimeError, HttpError, SSLError) as e:
        print(time.strftime('%X'), "Error getting values: {0}".format(e))


def print_files_in_folder(service, folder_id):
  """Print files belonging to a folder.

  Args:
    service: Drive API service instance.
    folder_id: ID of the folder to print files from.
  """
  page_token = None
  while True:
    try:
      param = {}
      if page_token:
        param['pageToken'] = page_token
      children = service.children().list(
          folderId=folder_id, **param).execute()

      for child in children.get('items', []):
        print('File Id: %s' % child['id'])
      page_token = children.get('nextPageToken')
      if not page_token:
        break
    except(errors.HttpError) as error:
      print('An error occurred: %s' % error)
      break



def flist(service):
    # Call the Drive v3 API
    results = service.files().list(
        pageSize=1000, fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])
    if not items:
        print('No files found.')
    else:
        print('Files:')
        for item in items:
            print('{0} ({1})'.format(item['name'], item['id']))

def files(service):
    page_token = None
    while True:
        response = service.files().list(q="name contains 'ccc'",
                                              spaces='drive',
                                              fields='nextPageToken, files(id, name, mimeType)',
                                              pageToken=page_token).execute()
        for file in response.get('files', []):
            # Process change
            print('Found file: %s (%s) (%s)' %(file.get('name'), file.get('id'), file.get('mimeType')))
        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break


def forms(service):
    page_token = None
    while True:
        response = service.files().list(q="mimeType = 'application/vnd.google-apps.form'",
                                              spaces='drive',
                                              fields='nextPageToken, files(id, name, mimeType)',
                                              pageToken=page_token).execute()
        for file in response.get('files', []):
            # Process change
            print('Found file: %s (%s) (%s)' %(file.get('name'), file.get('id'), file.get('mimeType')))
        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break

def spreadsheets(name):
    page_token = None
    result = []
    while True:
        response = metadata().files().list(q="name contains '" + name + "' and mimeType = 'application/vnd.google-apps.spreadsheet'",
                                              spaces='drive',
                                              fields='nextPageToken, files(id, name, mimeType)',
                                              pageToken=page_token).execute()
        for file in response.get('files', []):
            # Process change
            #print('Found file: %s (%s) (%s)' %(file.get('name'), file.get('id'), file.get('mimeType')))
            result.append(file)
        if page_token is None:
            break


    return result

def sheet(service, SPREADSHEET_ID, RANGE_NAME):
    # Call the Sheets API
    
    
    result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID,
                                                 range=RANGE_NAME).execute()
    values = result.get('values', [])
    if not values:
        print('No data found.')
        return None
    else:
        #print('Name, Major:')
        return values
        

def update(service, SPREADSHEET_ID, RANGE_NAME, tm):
    try:
        values = [[tm]]
        body = {'values': values}
        result = service.spreadsheets().values().update(spreadsheetId=SPREADSHEET_ID,
                                                        range=RANGE_NAME,
                                                        valueInputOption="RAW",
                                                        body=body).execute()
        #print('{0} cells updated.'.format(result.get('updatedCells')));
    except (RuntimeError, HttpError, SSLError) as e:
        print(time.strftime('%X'), "Error getting commands: {0}".format(e))

def createId(SPREADSHEET_ID, idx):
    try:
        id = time.time()
        service = sheets()
        values = [[id]]
        body = {'values': values}
        result = service.spreadsheets().values().update(spreadsheetId=SPREADSHEET_ID,
                                                        range="Form responses 1!B{0}".format(idx),
                                                        valueInputOption="RAW",
                                                        body=body).execute()
        return id
    except (RuntimeError, HttpError, SSLError) as e:
        print(time.strftime('%X'), "Error getting commands: {0}".format(e))
        return None

def folders(service):
    page_token = None
    while True:
        response = service.files().list(q="mimeType = 'application/vnd.google-apps.folder'",
                                              spaces='drive',
                                              fields='nextPageToken, files(id, name)',
                                              pageToken=page_token).execute()
        for file in response.get('files', []):
            # Process change
            print('Found folder: %s (%s)' %(file.get('name'), file.get('id')))
        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break

def openFile(service, file_id, mimeType):

    request = service.files().export_media(fileId=file_id, mimeType = 'application/vnd.google-apps.spreadsheet')
    fh = io.BytesIO()
    downloader = googleapiclient.http.MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        print("Download %d%%." % int(status.progress() * 100))


def comments(service, file_id):
    comments = service.comments().list(fileId=file_id).execute()
    #comments.get('items', [])
    for comment in comments:
        print(comment)

def getFileIds(files, key):
    for file in files:
        if file.get('name').endswith(key):
            return file.get('id')
    return None
