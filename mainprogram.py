import mysql.connector
from datetime import datetime
from datetime import timedelta

#Need to install Shaply library for this import: https://pypi.org/project/Shapely
from shapely.geometry import Point, Polygon

#Need to install Geopy library for this import: https://github.com/geopy/geopy
#It is used to calculate distance between 2 points given their coordinates
import geopy.distance

#Need to install prettytable library for this import: https://pypi.org/project/prettytable/
#Used to print data in pretty table
from prettytable import PrettyTable


#Global vars
fromDatetime = datetime.strptime('2015-01-10 00:00:00',"%Y-%m-%d %H:%M:%S") #datetime interval for the query
toDatetime = datetime.strptime('2015-01-10 00:10:00',"%Y-%m-%d %H:%M:%S")
delay = timedelta(minutes=5)          #timedelta object for tolerable delay

datetimeFormat = "%d-%b-%Y %H:%M:%S"
numRecordsToPrint = 600

#This is rough coordinates of Manhattan boundaries.
#The accuracy of these numbers are not reliable for
#high precision applications. See the image contained
#in the same folder of this file for more details.
#Sample tuple (latitude,longitude) . Latitude goes first.
manCoors=[(40.878528, -73.934173),(40.871745, -73.909575),
        (40.833877, -73.934173),(40.794892, -73.928385),
	      (40.732205, -73.966874),(40.709834, -73.976134),
        (40.699876, -74.017074),(40.755007, -74.011728)]

manPoly = Polygon(manCoors) #create a Manhattan polygon


#distance between points
def distance(*points):
    dist = 0
    p1 = points[0]
    for point in points:
        p2 = point
        dist = dist + geopy.distance.distance(p1, p2).miles
        p1 = p2
    return dist

#Function to check if a trip departs and arrives
#inside Manhattan. Will be passed to filter()
#Input: a list of trips
#Output: a list of trips
def isInManhattan(tuple):
  pickupPoint = Point(tuple[6],tuple[5]) #Point(latitude,longitude)
  dropoffPoint = Point(tuple[8],tuple[7])
  return pickupPoint.within(manPoly) and dropoffPoint.within(manPoly)

#Function to filter out trips have travel time = 0
def travelTimeNotZero(tuple):
  (_,pickupDateTime,dropoffDateTime,*therest) = tuple
  pu = pickupDateTime.strftime(datetimeFormat)
  do = dropoffDateTime.strftime(datetimeFormat)
  return pu != do


#Function to format datetime output. Will be passed to map()
def formatDatetime(tuple):
  (id,pickupDateTime,dropoffDateTime,*therest) = tuple
  newTuple = (id,pickupDateTime.strftime(datetimeFormat),
              dropoffDateTime.strftime(datetimeFormat),
              *therest)
  return newTuple

#Function to calculate straight-line distance D, speed V of a trip
def calculateDV(tuple):
    (id,startTime,endTime,*therest,startLong,startLat,endLong,endLat) = tuple
    startPoint = (startLat,startLong)
    endPoint = (endLat,endLong)
    dist = distance(startPoint, endPoint)
    dist = round(dist,2) #round to 2 decimals

    startTime = datetime.strptime(startTime, datetimeFormat) #convert to datetime object
    endTime = datetime.strptime(endTime,datetimeFormat)
    tripTime = endTime - startTime

    if(tripTime.total_seconds() == 0):
        return (*tuple,dist, 'N/A')

    speedMPS = dist / tripTime.total_seconds()
    speedMPH = round(speedMPS * 3600,2)
    return (*tuple,dist, speedMPH)

#Function to calculate speed in MPH of a trip
def speed(tuple):
    (id,startTime,endTime,*therest,startLong,startLat,endLong,endLat) = tuple
    startPoint = (startLat,startLong)
    endPoint = (endLat,endLong)
    dist = distance(startPoint, endPoint)
    dist = round(dist,2) #round to 2 decimals

    startTime = datetime.strptime(startTime, datetimeFormat) #convert to datetime object
    endTime = datetime.strptime(endTime,datetimeFormat)
    tripTime = endTime - startTime

    speedMPS = dist / tripTime.total_seconds()
    speedMPH = round(speedMPS * 3600,2)
    return speedMPH

#Calculate average speed of 2 strips
def avgSpeed(tup1, tup2):
    return round( (speed(tup1) + speed(tup2))/2, 2)

#Calculate distance saved and order of pickup/dropoff between 2 trips
def distanceSaved(t1, t2):
    
    #check passengers here
    (id1,_,_,t1_passengers,*theRest) = t1
    (id2,_,_,t2_passengers,*theRest) = t2
    if((t1_passengers + t2_passengers) > 3):
        return ("0","0","0","0",0)

    (_,startTime1,endTime1,*therest1,startLong1,startLat1,endLong1,endLat1) = t1
    startPoint1 = (startLat1,startLong1)
    endPoint1 = (endLat1,endLong1)
    st1 = datetime.strptime(startTime1, datetimeFormat)
    et1 = datetime.strptime(endTime1, datetimeFormat)

    (_,startTime2,endTime2,*therest2,startLong2,startLat2,endLong2,endLat2) = t2
    startPoint2 = (startLat2,startLong2)
    endPoint2 = (endLat2,endLong2)
    st2 = datetime.strptime(startTime2, datetimeFormat)
    et2 = datetime.strptime(endTime2, datetimeFormat)

    avgS = avgSpeed(t1, t2)
    if( avgS ==0 ):
        return ("0","0","0","0",0)

    singleTripsDistance = distance(startPoint1, endPoint1) + distance(startPoint2, endPoint2)

    resultDistance = 0
    resultSequence = 0

    #sequence 1: start1 start2 end1  end2
    #            stop1  stop2  stop3 stop4
    time_1_2 = timeBetween(startPoint1, startPoint2, avgS) #duration between stop 1 and 2
    time_2_3 = timeBetween(startPoint2, endPoint1, avgS)
    time_3_4 = timeBetween(endPoint1, endPoint2, avgS)
    at_stop_1 = st1                     #time at stop 1 when trips are merged
    at_stop_2 = at_stop_1 + time_1_2    #time at stop 2 when trips are merged
    at_stop_3 = at_stop_2 + time_2_3
    at_stop_4 = at_stop_3 + time_3_4

    #check if this sequence satisfies the delay
    if( ((st2 - at_stop_2) <= delay) and 
        ((st2 - at_stop_2) >= timedelta(seconds=0)) and
        ((at_stop_3 - et1) <= delay) and 
        ((at_stop_4 - et2) <= delay)
      ):
        
        mergedDistance = distance(startPoint1, startPoint2, endPoint1, endPoint2)

        #check if merged distance is less than individual distances
        if( mergedDistance < singleTripsDistance):
            
            savedDistance = singleTripsDistance - mergedDistance
            
            #if this sequence saves more miles, set it to result, saved distance has to be less than 20 miles to skip bad data
            if(savedDistance > resultDistance and savedDistance < 20):
                resultDistance = savedDistance
                resultSequence = 1

    #sequence 2: start1 start2 end2  end1
    #            stop1  stop2  stop3 stop4
    time_1_2 = timeBetween(startPoint1, startPoint2, avgS) #duration between stop 1 and 2
    time_2_3 = timeBetween(startPoint2, endPoint2, avgS)
    time_3_4 = timeBetween(endPoint2, endPoint1, avgS)
    at_stop_1 = st1                     #time at stop 1 when trips are merged
    at_stop_2 = at_stop_1 + time_1_2    #time at stop 2 when trips are merged
    at_stop_3 = at_stop_2 + time_2_3
    at_stop_4 = at_stop_3 + time_3_4

    #check if this sequence satisfies the delay
    if((st2 - at_stop_2) <= delay and (st2 - at_stop_2) >= timedelta(seconds=0)
            and (at_stop_3 - et2) <= delay and (at_stop_4 - et1) <= delay):
        
        mergedDistance = distance(startPoint1, startPoint2, endPoint2, endPoint1)

        #check if merged distance is less than individual distances
        if( mergedDistance < singleTripsDistance):
            
            savedDistance = singleTripsDistance - mergedDistance
            
            #if this sequence saves more miles, set it to result
            if(savedDistance > resultDistance and savedDistance < 20):
                resultDistance = savedDistance
                resultSequence = 2

    #sequence 3: start2 start1 end1  end2
    #            stop1  stop2  stop3 stop4
    time_1_2 = timeBetween(startPoint2, startPoint1, avgS) #duration between stop 1 and 2
    time_2_3 = timeBetween(startPoint1, endPoint1, avgS)
    time_3_4 = timeBetween(endPoint1, endPoint2, avgS)
    at_stop_1 = st2                     #time at stop 1 when trips are merged
    at_stop_2 = at_stop_1 + time_1_2    #time at stop 2 when trips are merged
    at_stop_3 = at_stop_2 + time_2_3
    at_stop_4 = at_stop_3 + time_3_4

    #check if this sequence satisfies the delay
    if((st1 - at_stop_2) <= delay and (st1 - at_stop_2) >= timedelta(seconds=0)
            and (at_stop_3 - et1) <= delay and (at_stop_4 - et2) <= delay):
        
        mergedDistance = distance(startPoint2, startPoint1, endPoint1, endPoint2)

        #check if merged distance is less than individual distances
        if( mergedDistance < singleTripsDistance):
            
            savedDistance = singleTripsDistance - mergedDistance
            
            #if this sequence saves more miles, set it to result
            if(savedDistance > resultDistance and savedDistance < 20):
                resultDistance = savedDistance
                resultSequence = 3

    #sequence 4: start2 start1 end2  end1
    #            stop1  stop2  stop3 stop4
    time_1_2 = timeBetween(startPoint2, startPoint1, avgS) #duration between stop 1 and 2
    time_2_3 = timeBetween(startPoint1, endPoint2, avgS)
    time_3_4 = timeBetween(endPoint2, endPoint1, avgS)
    at_stop_1 = st2                     #time at stop 1 when trips are merged
    at_stop_2 = at_stop_1 + time_1_2    #time at stop 2 when trips are merged
    at_stop_3 = at_stop_2 + time_2_3
    at_stop_4 = at_stop_3 + time_3_4

    #check if this sequence satisfies the delay
    if((st1 - at_stop_2) <= delay and (st1 - at_stop_2) >= timedelta(seconds=0)
            and (at_stop_3 - et2) <= delay and (at_stop_4 - et1) <= delay):
        
        mergedDistance = distance(startPoint2, startPoint1, endPoint2, endPoint1)

        #check if merged distance is less than individual distances
        if( mergedDistance < singleTripsDistance):
            
            savedDistance = singleTripsDistance - mergedDistance
            
            #if this sequence saves more miles, set it to result
            if(savedDistance > resultDistance and savedDistance < 20):
                resultDistance = savedDistance
                resultSequence = 4

    sequences = {0 : ("0","0","0","0",0),
                1 : ("o1","o2","d1","d2",resultDistance),
                2 : ("o1","o2","d2","d1",resultDistance),
                3 : ("o2","o1","d1","d2",resultDistance),
                4 : ("o2","o1","d2","d1",resultDistance)}
    return sequences[resultSequence]
                
            
#Calculate the time travel(in seconds) between 2 points given the speed
def timeBetween(p1, p2, speed):
    distance = geopy.distance.distance(p1, p2).miles
    speedMPS = speed/3600
    return timedelta(seconds=round(distance/speedMPS, 2))

#Function to make rideshare record given 2 trips and their order
def rideShareRec(t1, t2, orderTup):
    order = orderTup[0] + " " + orderTup[1] + " " + orderTup[2] + " " + orderTup[3]
    savedDist = round(orderTup[4],2)
    (*theRest1, puLong1, puLat1, doLong1, doLat1) = t1
    (*theRest2, puLong2, puLat2, doLong2, doLat2) = t2
    return ((puLat1,puLong1),(doLat1,doLong1),(puLat2,puLong2),(doLat2,doLong2),
            savedDist, order)

#function to convert a list to a hash map
#This list is the result came directly from the query
def toMap(ls):
    length = len(ls)
    dic = {}
    for i in range(0,length):
        dic[i] = ls[i]
    return dic


#Connect to database. Replace user and password
#of your own machine. And the name of the database
#you created for the project.
db = mysql.connector.connect (
	host = 'localhost',
	user = 'root',
	password = 'nooneknow',
	database = 'CS480_Project'
)
cursor = db.cursor()


mergedTrips = list()
milesSaved = 0
queriesCount = 0
queriesTime = 0 #in seconds
tripsCount = 0

fromTime = fromDatetime
toTime = fromTime + delay

programStart = datetime.now() #to measure the program running time ( main() starts here)
while(toTime <= toDatetime):
    fromTimeString = datetime.strftime(fromTime, "%Y-%m-%d %H:%M:%S")
    toTimeString = datetime.strftime(toTime, "%Y-%m-%d %H:%M:%S")
    
    queryStartTime = datetime.now()
    cursor.execute(
    f"""
    SELECT id, PickupDateTime, DropoffDateTime, PassengerCount, Distance,
          PickupLongitude, PickupLatitude, DropoffLongitude, DropoffLatitude
    FROM yellow_2015_01
    WHERE PickupDateTime BETWEEN '{fromTimeString}' AND '{toTimeString}'
        AND PassengerCount < 3
    ORDER BY PickupDateTime;
    """
    )
    queryFinishTime = datetime.now()
    queryResult = cursor.fetchall()

    #allTripsQueryTime = str(queryFinishTime - queryStartTime)[:-4]
    tripsCount = tripsCount + len(queryResult)
    queriesTime = queriesTime + (queryFinishTime - queryStartTime).total_seconds() #add to total time
    queriesCount = queriesCount + 1
    
    
    #filter trips have zero travel time(startTime == endTime)
    queryResult = list(filter(travelTimeNotZero,queryResult))

    #format datetime output to be readable. Convert to list afterward
    queryResult = list(map(formatDatetime,queryResult))

    resultMap = toMap(queryResult)
    mapLength = len(resultMap)

    for i in range(0, mapLength):
        #display process
        milesSavedString = str(round(milesSaved,2)).ljust(10)
        print("Miles saved: ",milesSavedString," Trips merged: ",str(len(mergedTrips)*2),
                "/",mapLength)
        
        if(len(resultMap[i]) ==0): #trip is already merged
            continue
        
        
        result = ("0","0","0","0",0) #tuple holds order and mileage saved. See line 250 for example
        otherTrip = () #place holder
        otherTripKey = 0 #place holder
        mile = 0 #place holder
        for j in range(i+1, mapLength):
            if(len(resultMap[j]) ==0): #trip is already merged
                continue

            #check if 2 trips are mergeable and calculate miles saved
            saved = distanceSaved(resultMap[i],resultMap[j])
            
            if(saved[4] > result[4]): #if the saved miles is more than current, set current to this saved miles
                result = saved
                mile = saved[4] #accumulatee for miles saved
                otherTrip = resultMap[j] #set current other trip to the new trip
                otherTripKey = j #need key to use outside of for-loop
        
        if(otherTripKey != 0): #there are a mergeable trip
            milesSaved = milesSaved + mile #accumulate miles saved
            
            #create tuple of 2 trips then add the tuple to the result
            mergedTrips.append(rideShareRec(resultMap[i],otherTrip, result))
            
            resultMap[otherTripKey] = () #remove by assigning empty tuple
            
        resultMap[i] = () #remove current trip

    #update to the next time window
    fromTime = toTime
    toTime = toTime + delay
    
    #the remaing time (last time window)
    if(toTime > toDatetime and toTime < (toDatetime + delay)):
        toTime = toDatetime
#end while-loop


programExecTime = (datetime.now() - programStart).total_seconds() #in seconds

dataTable = PrettyTable(['Origin 1 (Lat,Long)','Destination 1','Origin 2','Destination 2',
    'Mileage Saved','Pickup/Dropoff Order'])
for i in range(0,numRecordsToPrint):
    dataTable.add_row([*mergedTrips[i]]) #unpack tuple to make array

print(dataTable)
print("Rows displayed: ",numRecordsToPrint)
print("Number of trips retrieved: ", tripsCount)
print("Merged trips: ", len(mergedTrips) * 2)
print("Total mileage saved: ",round(milesSaved,2))
print("Trips after merging: ",len(mergedTrips))
print("Mergeable trips percentage: ",round((len(mergedTrips)*2)/tripsCount*100,2),'%')
print("Program execution time: ", programExecTime,"s")
print("Average queries execution time: ", round(queriesTime/queriesCount,2),"s")
