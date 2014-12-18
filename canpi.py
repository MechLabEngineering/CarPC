import mhsTinyCanDriver
import time

if __name__ == '__main__':
	
	# create the driver
	canDriver = mhsTinyCanDriver.MhsTinyCanDriver(0,options = {'CanRxDMode':1,
		'AutoConnect':1,
		'CanSpeed1':250})
		
	polltime = 0.5
	log = open("CANlog.txt","w")

	try:
		while True:
			print('Polling Rx FIFO - Filter')
			myFilterCount = canDriver._CanReceiveGetCount(canDriver.Index)
			print('{0} Messages in FiFO'.format(myFilterCount))
			if myFilterCount:
				msg = canDriver.CanReceiveAndFormatSimple(canDriver.Index,count = myFilterCount)
				print(msg) 
				for m in msg:
					log.write(m+'\n')                                      
			time.sleep(polltime)    
	except KeyboardInterrupt:
		pass
		
	# shutdown
	canDriver.resetCanBus()
	canDriver._CanDownDriver()
	canDriver.so = None
	
	log.close()
	
	
	print ('done')
