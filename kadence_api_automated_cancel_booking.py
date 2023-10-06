import sys
import json
import requests
import schedule
import time
from datetime import datetime, timezone
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta

def getCredentials(credential_file):
    with open(credential_file) as f:
        reader = json.load(f)
        print(reader)
    return reader.get('credential_id'), reader.get('credential_secret')

def authenticate(url, client_id, client_secret):
    auth_url = url
    token_req_payload = {
        'grant_type': 'client_credentials', 
        'client_id':client_id, 
        'client_secret': client_secret,
        'scope':'public'
        }
    token = requests.post(auth_url, data=token_req_payload)
    if token.status_code != 200:
        print("Failed to obtain token from Oauth2.0 server", file=sys.stderr)
        sys.exit(1)
    print("Successfully obtained a new token")
    tokens = json.loads(token.text)
    print(tokens['access_token'])
    return tokens['access_token']

def toFile(filename, json_data):
    jsonified_content = json.dumps(json_data, indent=4)
    f = open('kadence_api_audit_{}.json'.format(filename),'w')
    f.write(jsonified_content)
    f.close()

def getUsers(header):
    url = 'https://api.onkadence.co/v1/public/users'
    response = requests.get(url, params={'itemsPerPage':500}, headers=header)
    toFile('Users', response.json())
    userSimplified = []
    userList = []
    for item in response.json()['hydra:member']:
        userSimplified.append(
            {
                'userId': item['id'],
                'firstName': item['firstName'],
                'lastName': item['lastName']
            })
        userList.append(item['id'])
    toFile('Users_simplified', {'hydra:member': userSimplified})
    return userList

def logBookings(header):
    url = 'https://api.onkadence.co/v1/public/bookings'
    response = requests.get(url, headers=header)
    toFile('Bookings', response.json())
    return response.json()

def getTodayUserBookings(header,userId):
    url = 'https://api.onkadence.co/v1/public/users/{}/bookings'.format(userId)
    startTime = datetime.today().strftime('%Y-%m-%dT') + '09:00:00' + '+00:00' # 9:00 AM + TimezoneDiff
    endTime = datetime.today().strftime('%Y-%m-%dT') + '17:00:00' + '+00:00' # 5:00 PM + TimezoneDiff
    print(startTime, endTime)
    response = requests.get(url, headers=header, params={ 'startDateTime[after]': startTime, 'endDateTime[before]': endTime})
    toFile('RonaldLin', response.json())
    return response.json()

def performCancellation(header):
    userList = getUsers(header)
    # This for-loop should only be used if performing org-wide employee booking cancellations
    #for userId in userList:
        #bookingIds = getSpecificUserBookings(header, userId)
    userId
    bookingIds = getTodayUserBookings(header, userId)
    for bookingId in bookingIds['hydra:member']:
        nowTime = parse((datetime.now().strftime('%Y-%m-%dT%H:%M:%S') + '+00:00'))
        startTime = parse(bookingId['startDate'])
        delta = relativedelta(nowTime, startTime)
        print(nowTime, startTime, delta)
        if bookingId['status'] == 'Booked' and (delta.hours > 0 or delta.minutes > 30):
            cancelBooking(header, userId, bookingId)
    print('Updated booking!')

def cancelBooking(header, userId, bookingId):
        url = 'https://api.onkadence.co/v1/public/bookings/{}/cancel'.format(bookingId['id'])
        header['Accept'] = 'application/ld+json'
        response = requests.post(url, headers=header, json={ 'userId': userId })
        #toFile('cancel', response.json())
        print(json.dumps(response.json(),indent=4))

def main():
    # INITIALIZATION
    print('Process initiating... Automating booking cancellation module.')
    client_id, client_secret = getCredentials('kadence_api_key.json')
    myToken = authenticate('https://login.onkadence.co/oauth2/token', client_id, client_secret)
    header = {'Authorization': 'Bearer {}'.format(myToken)}
    # TASK PERFORM
    while True:
        print('Updating booking every 30 seconds...')
        performCancellation(header)
        time.sleep(30) # check every 30 seconds

if __name__ == '__main__':
    main()
