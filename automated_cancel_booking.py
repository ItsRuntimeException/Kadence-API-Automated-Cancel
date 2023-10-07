import sys
import json
import requests
import time
from datetime import datetime, timedelta
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
    #print(tokens['access_token'])
    return tokens['access_token']

def toFile(filename, json_data):
    jsonified_content = json.dumps(json_data, indent=4)
    f = open('kadence_api_audit_{}.json'.format(filename),'w')
    f.write(jsonified_content)
    f.close()

def getUsers(header):
    url = 'https://api.onkadence.co/v1/public/users'
    response = requests.get(url, params={'itemsPerPage':500}, headers=header)
    userSimplified = []
    userList = []
    for item in response.json()['hydra:member']:
        userSimplified.append(
            {
                'userId': item['id'],
                'email': item['email'],
                'firstName': item['firstName'],
                'lastName': item['lastName']
            })
        userList.append(item['id'])
    #toFile('Users', response.json())
    toFile('Users_simplified', {'hydra:member': userSimplified})
    return userList

def logBookings(header):
    url = 'https://api.onkadence.co/v1/public/bookings'
    response = requests.get(url, headers=header)
    toFile('Bookings', response.json())
    return response.json()

def getTodayUserBookings(header,userId):
    url = 'https://api.onkadence.co/v1/public/users/{}/bookings'.format(userId)
    # GET DATE RANGE OF 1 DAY:
    startTime = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    endTime = datetime.now() + timedelta(days=1)
    endTime = endTime.astimezone().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    print('Gathering time range between: {} - {}'.format(startTime, endTime))
    response = requests.get(url, headers=header, params={ 'startDateTime[after]': startTime, 'endDateTime[before]': endTime})
    toFile('myBookings', response.json())
    return response.json()

def cancelBooking(header, userId, bookingId):
        url = 'https://api.onkadence.co/v1/public/bookings/{}/cancel'.format(bookingId['id'])
        header['Accept'] = 'application/ld+json'
        response = requests.post(url, headers=header, json={ 'userId': userId })
        print(json.dumps(response.json(),indent=4))

def performCancellation(header):
    userList = getUsers(header)
    #for userId in userList:
        #bookingIds = getSpecificUserBookings(header, userId)
    userId='<INPUT_USERID_HERE>'
    bookingIds = getTodayUserBookings(header, userId)
    print('\nAudit:')
    for bookingId in bookingIds['hydra:member']:
        nowTime = parse(datetime.now().astimezone().replace(microsecond=0).isoformat())
        startTime = parse(bookingId['startDate'])
        delta = relativedelta(nowTime, startTime)
        print(nowTime, startTime, delta)
        if (delta.hours > 0 or delta.minutes > 30) and bookingId['status'] == 'booked':
            cancelBooking(header, userId, bookingId)
            print('Cancelled unchecked-in booking!')

def main():
    # INITIALIZATION
    print('Process initiating... Automating booking cancellation module.')
    client_id, client_secret = getCredentials('kadence_api_key.json')
    myToken = authenticate('https://login.onkadence.co/oauth2/token', client_id, client_secret)
    header = {'Authorization': 'Bearer {}'.format(myToken)}
    # TASK PERFORM
    while True:
        print('Updating booking every 5 minutes...')
        performCancellation(header)
        time.sleep(300) # check every 30 seconds

if __name__ == '__main__':
    main()
