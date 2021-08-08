import mysql.connector
from datetime import datetime

#Need to install Shaply library for this import: https://pypi.org/project/Shapely
from shapely.geometry import Point, Polygon

#Need to install Geopy library for this import: https://github.com/geopy/geopy
#It is used to calculate distance between 2 points given their coordinates
import geopy.distance

#Need to install prettytable library for this import: https://pypi.org/project/prettytable/
#Used to print data in pretty table
from prettytable import PrettyTable


#Global vars
fromDatetime = "'2015-01-10'"         #datetime interval for the query
toDatetime = "'2015-01-10 00:04:59'"

datetimeFormat = "%d-%b-%Y %H:%M:%S"
numRecordsToPrint = 50

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


#Function to check if a trip departs and arrives
#inside Manhattan. Will be passed to filter()
#Input: a list of trips
#Output: a list of trips
def isInManhattan(tuple):
  pickupPoint = Point(tuple[5],tuple[4]) #Point(latitude,longitude)
  dropoffPoint = Point(tuple[7],tuple[6])
  return pickupPoint.within(manPoly) and dropoffPoint.within(manPoly)

#Function to format datetime output. Will be passed to map()
def formatDatetime(tuple):
  (pickupDateTime,dropoffDateTime,*therest) = tuple
  newTuple = (pickupDateTime.strftime(datetimeFormat),
              dropoffDateTime.strftime(datetimeFormat),
              *therest)
  return newTuple

#Function to calculate straight-line distance D, speed V of a trip
def calculateDV(tuple):
    (startTime,endTime,*therest,startLong,startLat,endLong,endLat) = tuple
    startPoint = (startLat,startLong)
    endPoint = (endLat,endLong)
    distance = geopy.distance.distance(startPoint, endPoint).miles
    distance = round(distance,2) #round to 2 decimals

    startTime = datetime.strptime(startTime, datetimeFormat) #convert to datetime object
    endTime = datetime.strptime(endTime,datetimeFormat)
    tripTime = endTime - startTime

    if(tripTime.total_seconds() == 0):
        return (*tuple,distance, 'N/A')

    speedMPS = distance / tripTime.total_seconds()
    speedMPH = round(speedMPS * 3600,2)
    return (*tuple,distance, speedMPH)

#Function to check if 2 trips are mergable(todo)

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

queryStartTime = datetime.now()
cursor.execute(
f"""
SELECT PickupDateTime, DropoffDateTime, PassengerCount, Distance, 
	  PickupLongitude, PickupLatitude, DropoffLongitude, DropoffLatitude
FROM yellow_2015_01 
WHERE PickupDateTime BETWEEN {fromDatetime} AND {toDatetime}
ORDER BY PickupDateTime;
"""
)
queryFinishTime = datetime.now()
result = cursor.fetchall()

allTripsQueryTime = str(queryFinishTime - queryStartTime)[:-4] #convert to string then chop off the last 4 decimal places
allTripsNum = len(result)



queryStartTime = datetime.now()
cursor.execute(
f"""
SELECT PickupDateTime, DropoffDateTime, PassengerCount, Distance, 
	  PickupLongitude, PickupLatitude, DropoffLongitude, DropoffLatitude
FROM yellow_2015_01 
WHERE PickupDateTime BETWEEN {fromDatetime} AND {toDatetime}
    AND PassengerCount < 3
ORDER BY PickupDateTime;
"""
)
queryFinishTime = datetime.now()
result = cursor.fetchall()

mergableTripsQueryTime = str(queryFinishTime - queryStartTime)[:-4]
mergableTripsNum = len(result)



#filter Manhattan trips.Convert to list afterward
manTrips = list(filter(isInManhattan,result))

#format datetime output to be readable. Convert to list afterward
manTrips = list(map(formatDatetime,manTrips))

#add distance, and speed columns to table
manTrips = list(map(calculateDV,manTrips))

dataTable = PrettyTable(['Departure','Arrival','Passengers','RealDistance',
    'PickupLong','PickupLat','DropoffLong','DropoffLat',
    'StraightlineDist','StraightlineSpeed'])
for i in range(0,numRecordsToPrint):
    dataTable.add_row([*manTrips[i]]) #unpack tuple to make array

print(dataTable)
print("Rows displayed: ",numRecordsToPrint)
print("Number of trips of given interval: ", allTripsNum,
        " Query execution time: ",allTripsQueryTime,"s")
print("Number of mergable trips(trips have less than 3 passengers): ", mergableTripsNum,
        " Query execution time: ",mergableTripsQueryTime, "s")
print("Manhattan trips: ",len(manTrips))
print("Mergable trips percentage: ",
        round(mergableTripsNum/allTripsNum*100,2),'%')
