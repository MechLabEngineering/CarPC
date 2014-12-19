#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009, Rene Maurer <rene@cumparsita.ch>
# Copyright (C) 2009, omnitron.ch/allevents.ch
#
# Ported to Python3 by
# Copyright (C) 2014, Patrick Menschel <menschel.p@posteo.de>
# 
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see http://www.gnu.org/licenses.
#
# Description
#   This file/module contains the class 'MhsTinyCanDriver' which
#   represents a driver for the MHS Tiny-CAN modules. Look at
#   http://www.tiny-can.de
#   for details.
#
# Usage
#   python MhsTinyCanDriver.py -h
#   see __main__ section at the end of this file for details.
#
# Requirments
#   The shared library for your MHS CAN module:
#   - libmhstcan.so   (TESTED)

#
#   The library/libraries must be present in one of the following
#   locations:
#   - .            (current directory)
#   - ./lib        (lib in current directory)
#   - /usr/local/lib
#   - /usr/lib
#
# TODO
#   Callback functions (not implemented)
# ---------------------------------------------------------------------- 
# ChangeLog: 
# 08.12.2013 V0.53 Changed to Python3, P.Menschel (menschel.p@posteo.de)
# 02.01.2014 V0.54 Many Functions redone, Complete Event Handling Implemented, P.Menschel (menschel.p@posteo.de)
#                  Changed Option Handling to Dictionary, XHandling of Status Values to readable Status Info  
# 12.01.2014 V0.55 Read path of the Tiny-CAN API DLL from the windows registry
# ---------------------------------------------------------------------- 
#  DLL/SO Buglist/Issues
# - EFF Flag in FilterFlags seems unimplemented, setting it makes the filter not work 
# - RX Event Handling of Indexes set by Filters does fail with more than one filter set, all RX Events are flushed to INDEX 0, so it seems
# - PNP Event CONNECT does not work on linux at all, same Script works on Windows ok
# ---------------------------------------------------------------------- 

VERSION = \
"""
MhsTinyCanDriver V0.55, 12.01.2014 (LGPL)
Last Change: P.Menschel (menschel.p@posteo.de)
"""
from ctypes import Structure,c_int,c_ubyte,c_ulong,c_char_p,c_ushort,pointer,Union,POINTER
import os
import sys
import time
import uselogging
from utils import OptionDict2CsvString,UpdateOptionDict,CsvString2OptionDict

if sys.platform == "win32":
    from ctypes import WinDLL,WINFUNCTYPE
    from _winreg import OpenKey,CloseKey,QueryValueEx,HKEY_LOCAL_MACHINE,KEY_ALL_ACCESS
else:
    from ctypes import CDLL,CFUNCTYPE  


# locations where we look for shared libraries
if sys.platform == "win32":
    REG_TINY_CAN_API = r'Software\Tiny-CAN\API'
    REG_TINY_CAN_API_PATH_ENTRY = r'PATH'
    try:
        key = OpenKey(HKEY_LOCAL_MACHINE, REG_TINY_CAN_API, 0, KEY_ALL_ACCESS)
        mhs_api_path = QueryValueEx(key, REG_TINY_CAN_API_PATH_ENTRY)
    except:
        sharedLibraryLocations = [os.curdir]
    else:
        sharedLibraryLocations = [mhs_api_path[0], os.curdir]
    finally:
        if vars().has_key('key'):            
            CloseKey(key)        
else:
    sharedLibraryLocations = [os.curdir,
                              os.path.join(os.curdir,'lib'),
                              os.path.join('usr','local','lib'),
                              os.path.join('usr','lib')]
    
# Menschel 19.12.2013 - Start
# CAN Bitrates
CAN_10K_BIT     = 10
CAN_20K_BIT     = 20
CAN_50K_BIT     = 50
CAN_100K_BIT    = 100
CAN_125K_BIT    = 125
CAN_250K_BIT    = 250
CAN_500K_BIT    = 500
CAN_800K_BIT    = 800
CAN_1M_BIT      = 1000

canBitrates = [
               CAN_10K_BIT,
               CAN_20K_BIT,
               CAN_50K_BIT,
               CAN_100K_BIT,
               CAN_125K_BIT,
               CAN_250K_BIT,
               CAN_500K_BIT,
               CAN_800K_BIT,
               CAN_1M_BIT
               ]

TCAN_ERROR_CODES = {-1:'Driver not initialized',
                    -2:'Called with Invalid Parameters',
                    -3:'Invalid Index',
                    -4:'Invalid CAN Channel',
                    -5:'Common Error',
                    -6:'FIFO Write Error',
                    -7:'Buffer Write Error',
                    -8:'FIFO Read Error',
                    -9:'Buffer Read Error',
                    -10:'Variable not found',
                    -11:'Variable is not readable',
                    -12:'Read Buffer to small for Variable',
                    -13:'Variable is not writable',
                    -14:'Write Buffer to small for Variable',
                    -15:'Below Minimum Value',
                    -16:'Above Maximum Value',
                    -17:'Access Denied',
                    -18:'Invalid CAN Speed',
                    -19:'Invalid Baud Rate',
                    -20:'Variable not assigned',
                    -21:'No Connection to Hardware',
                    -22:'Communication Error with Hardware',
                    -23:'Hardware sends wrong Number of Parameters',
                    -24:'RAM Memory too low',
                    -25:'OS does not provide enough resources',
                    -26:'OS Syscall Error',
                    -27:'Main Thread is busy'}

# Driver Status Modes
DRV_NOT_LOAD             = 0 # Driver not loaded (although impossible)
DRV_STATUS_NOT_INIT      = 1 # Driver not initialized
DRV_STATUS_INIT          = 2 # Driver is inialized
DRV_STATUS_PORT_NOT_OPEN = 3 # Port is not open
DRV_STATUS_PORT_OPEN     = 4 # Port is open
DRV_STATUS_DEVICE_FOUND  = 5 # Device was found / is connected
DRV_STATUS_CAN_OPEN      = 6 # Device is initialized and open
DRV_STATUS_CAN_RUN_TX    = 7 # Can Bus Transmit only (not used!)
DRV_STATUS_CAN_RUN       = 8 # CAN Bus is active
DRIVER_STATUS_MODES = {DRV_NOT_LOAD:'DRV_NOT_LOAD',
                       DRV_STATUS_NOT_INIT:'DRV_STATUS_NOT_INIT',
                       DRV_STATUS_INIT:'DRV_STATUS_INIT',
                       DRV_STATUS_PORT_NOT_OPEN:'DRV_STATUS_PORT_NOT_OPEN',
                       DRV_STATUS_PORT_OPEN:'DRV_STATUS_PORT_OPEN',
                       DRV_STATUS_DEVICE_FOUND:'DRV_STATUS_DEVICE_FOUND',
                       DRV_STATUS_CAN_OPEN:'DRV_STATUS_CAN_OPEN',
                       DRV_STATUS_CAN_RUN_TX:'DRV_STATUS_CAN_RUN_TX',
                       DRV_STATUS_CAN_RUN:'DRV_STATUS_CAN_RUN'}
 
# Fifo Status Modes
FIFO_STATUS_OK          = 0 # FIFO_STATUS_OK
FIFO_STATUS_OVERRUN     = 1 # FIFO STATUS OVERRUN
FIFO_STATUS_INVALID     = 2 # FIFO STATUS INVALID
FIFO_STATUS_Unknown     = 4 # FIFO STATUS Unknown Undocumented
FIFO_STATUS_MODES = {FIFO_STATUS_OK:'FIFO_STATUS_OK',
                     FIFO_STATUS_OVERRUN:'FIFO_STATUS_OVERRUN',
                     FIFO_STATUS_INVALID:'FIFO_STATUS_INVALID',
                     FIFO_STATUS_Unknown:'FIFO_STATUS_Unknown'}

# Can Status Modes
CAN_STATUS_OK           = 0 # Can Status OK
CAN_STATUS_ERROR        = 1 # Can Status ERROR
CAN_STATUS_WARNING      = 2 # Can Status WARNING
CAN_STATUS_PASSIVE      = 3 # Can Status Passive
CAN_STATUS_BUS_OFF      = 4 # Can Status BUS OFF
CAN_STATUS_INVALID      = 5 # Can Status INVALID
CAN_STATUS_MODES = {CAN_STATUS_OK:'CAN_STATUS_OK',
                    CAN_STATUS_ERROR:'CAN_STATUS_ERROR',
                    CAN_STATUS_WARNING :'CAN_STATUS_WARNING',
                    CAN_STATUS_PASSIVE:'CAN_STATUS_PASSIVE',
                    CAN_STATUS_BUS_OFF:'CAN_STATUS_BUS_OFF',
                    CAN_STATUS_INVALID:'CAN_STATUS_INVALID'}

# CAN Bus Modes
OP_CAN_NO_CHANGE        = 0 # No Change 
OP_CAN_START            = 1 # Start CAN
OP_CAN_STOP             = 2 # Stop CAN
OP_CAN_RESET            = 3 # Reset CAN
OP_CAN_LOM              = 4 # Listen Only Mode
OP_CAN_START_NO_RETRANS = 5 # No Auto Retransmission

CAN_BUS_MODES = {OP_CAN_NO_CHANGE:'OP_CAN_NO_CHANGE',
                 OP_CAN_START:'OP_CAN_START',
                 OP_CAN_STOP:'OP_CAN_STOP',
                 OP_CAN_RESET:'OP_CAN_RESET',
                 OP_CAN_LOM:'OP_CAN_LOM',
                 OP_CAN_START_NO_RETRANS:'OP_CAN_START_NO_RETRANS'}


# Command
CAN_CMD_NONE                = 0x0000 # CAN COMMAND NONE
CAN_CMD_RXD_OVERRUN_CLEAR   = 0x0001 # CAN Clear Receive Overrun Error
CAN_CMD_RXD_FIFOS_CLEAR     = 0x0002 # CAN Clear Receive FIFOs
CAN_CMD_TXD_OVERRUN_CLEAR   = 0x0004 # CAN Clear Transmit Overrun Error
CAN_CMD_TXD_FIFOS_CLEAR     = 0x0008 # CAN Clear Transmit FIFOs
CAN_CMD_HW_FILTER_CLEAR     = 0x0010 # CAN Clear HW Filters
CAN_CMD_SW_FILTER_CLEAR     = 0x0020 # CAN Clear SW Filters
CAN_CMD_TXD_BUFFER_CLEAR    = 0x0040 # CAN Clear Transmit Buffers (Interval Messages) 
CAN_CMD_ALL_CLEAR           = 0x0FFF # CAN Clear All Receive/Transmit Errors/FIFOs, SW/HW FILTERS


# SetEvent
EVENT_ENABLE_PNP_CHANGE             = 0x0001 # Enable Plug & Play Event 
EVENT_ENABLE_STATUS_CHANGE          = 0x0002 # Enable CAN Status Change Event
EVENT_ENABLE_RX_FILTER_MESSAGES     = 0x0004 # Enable CAN Receive Event for Filtered Messages
EVENT_ENABLE_RX_MESSAGES            = 0x0008 # Enable CAN Receive Event
EVENT_ENABLE_ALL                    = 0x00FF # Enable all Events
EVENT_DISABLE_PNP_CHANGE            = 0x0100 # Disable Plug & Play Event 
EVENT_DISABLE_STATUS_CHANGE         = 0x0200 # Disable CAN Status Change Event
EVENT_DISABLE_RX_FILTER_MESSAGES    = 0x0400 # Disable CAN Receive Event for Filtered Messages
EVENT_DISABLE_RX_MESSAGES           = 0x0800 # Disable CAN Receive Event
EVENT_DISABLE_ALL                   = 0xFF00 # Disable all Events

# Global Options Dictionary for TCAN API

TCAN_Options = {'CanRxDFifoSize':None,
                'CanTxDFifoSize':None,
                'CanRxDMode':None,
                'CanRxDBufferSize':None,
                'CanCallThread':None,
                'MainThreadPriority':None,
                'CallThreadPriority':None,
                'Hardware':None,
                'CfgFile':None,
                'Section':None,
                'LogFile':None,
                'LogFlags':None,
                'TimeStampMode':None,
                'CanTxAckEnable':None,
                'CanSpeed1':None,
                'CanSpeed1User':None,
                'AutoConnect':None,
                'AutoReopen':None,
                'MinEventSleepTime':None,
                'ExecuteCommandTimeout':None,
                'LowPollIntervall':None,
                'FilterReadIntervall':None,
                'Port':None,
                'ComDeviceName':None,
                'BaudRate':None,
                'VendorId':None,
                'ProductId':None,
                'Snr':None}

TCAN_Keys_CanInitDriver=['CanRxDFifoSize',
                         'CanTxDFifoSize',
                         'CanRxDMode',
                         'CanRxDBufferSize',
                         'CanCallThread',
                         'MainThreadPriority',
                         'CallThreadPriority',
                         'Hardware',
                         'CfgFile',
                         'Section',
                         'LogFile',
                         'LogFlags',
                         'TimeStampMode']
TCAN_Keys_CanDeviceOpen = ['Port',
                           'ComDeviceName',
                           'BaudRate',
                           'VendorId',
                           'ProductId',
                           'Snr']
TCAN_Keys_CanSetOption = ['CanTxAckEnable',
                          'CanSpeed1',
                          'CanSpeed1User',
                          'AutoConnect',
                          'AutoReopen',
                          'MinEventSleepTime',
                          'ExecuteCommandTimeout',
                          'LowPollIntervall',
                          'FilterReadIntervall']
# TIndex
class TIndexBits(Structure):
    _fields_ = [
                ('SubIndex',c_ushort),#16bit
                ('CanChannel',c_ubyte,4),#4bit
                ('CanDevice',c_ubyte,4),#4bit
                ('RxTxFlag',c_ubyte,1),#1bit
                ('SoftFlag',c_ubyte,1),#1bit
                ('Reserved',c_ubyte,6)#6bit
                ]#32bits total
    def __init__(self):
        self.SubIndex=0
        self.CanChannel=0
        self.CanDevice=0
        self.RxTxFlag=0
        self.SoftFlag=0
        self.Reserved=0

class TIndex(Union):
    _fields_ = [('IndexBits',TIndexBits),
                ('Uint32',c_ulong)]
    def __init__(self):
        self.Uint32 = 0

# Menschel 19.12.2013 - End
 
# TDeviceStatus
class TDeviceStatus(Structure):
    _fields_ = [('DrvStatus', c_int),
                ('CanStatus', c_ubyte),
                ('FifoStatus', c_ubyte)]
# Menschel 19.12.2013 - Start
    def __init__(self):
        self.DrvStatus = 0
        self.CanStatus = 0
        self.FifoStatus = 0
# Menschel 19.12.2013 - End

# TCANFlagBits
class TCANFlagBits(Structure):
    _fields_ = [('DLC',c_ubyte,4),#4bit
                ('TxD',c_ubyte,1),#1bit
                ('Reserved1',c_ubyte,1),#1bit
                ('RTR',c_ubyte,1),#1bit
                ('EFF',c_ubyte,1),#1bit
                ('Source',c_ubyte),#8bit
                ('Reserved2',c_ushort)#16bit
                ]#32bits total
# Menschel 19.12.2013 - Start    
    def __init__(self):
        self.DLC=0
        self.TxD=0
        self.Reserved1=0
        self.RTR=0
        self.EFF=0
        self.Source=0
        self.Reserved2=0


class TCANFlags(Union):
    _fields_ = [('FlagBits',TCANFlagBits),
                ('Uint32',c_ulong)]    
# Menschel 19.12.2013 - End
        
# TCanMsg
class TCanMsg(Structure):
    _fields_ = [('Id', c_ulong),
                ('Flags', TCANFlags),
                ('Data', c_ubyte * 8),
                ('Sec', c_ulong),
                ('USec', c_ulong)]
# Menschel 19.12.2013 - Start
    def __init__(self):
        self.Id=0
        self.Flags.Uint32=0
        self.Data=0,0,0,0,0,0,0,0
        self.Sec=0
        self.USec=0

class TMsgFilterFlagsBits(Structure):
    _fields_ = [('DLC',c_ubyte,4),#4bit
                ('Reserved1',c_ubyte,2),#2bit
                ('RTR',c_ubyte,1),#1bit
                ('EFF',c_ubyte,1),#1bit
                
                ('IdMode',c_ubyte,2),#2bit
                ('DlcCheck',c_ubyte,1),#1bit
                ('DataCheck',c_ubyte,1),#1bit
                ('Reserved2',c_ubyte,4),#4bit
                
                ('Reserved3',c_ubyte),#8bit
                
                ('Type',c_ubyte,4),#4bit
                ('Reserved4',c_ubyte,2),#2bit
                ('Mode',c_ubyte,1),#1bit
                ('Enable',c_ubyte,1)#1bit
                ]#32bits total
    
    def __init__(self):
        self.DLC = 0
        self.Reserved1 = 0
        self.RTR = 0
        self.EFF = 0
        self.IdMode = 0
        self.DlcCheck = 0
        self.DataCheck = 0
        self.Reserved2 = 0
        self.Reserved3 = 0
        self.Type = 0
        self.Reserved4 = 0
        self.Mode = 0
        self.Enable = 0
    
class TMsgFilterFlags(Union):
    _fields_ = [('FlagBits',TMsgFilterFlagsBits),
                ('Uint32',c_ulong)]       
# Menschel 19.12.2013 - End

# TMsgFilter
class TMsgFilter(Structure):
    _fields_ = [('Mask', c_ulong),
                ('Code', c_ulong),
                ('Flags', TMsgFilterFlags)]
    
# Menschel 19.12.2013 - Start
    def __init__(self):
        self.Mask=0
        self.Code=0
        self.Flags.Uint32=0
# Menschel 19.12.2013 - End

# --------------------------------------------------------------------
# ------------------ Driver Class ------------------------------------
# --------------------------------------------------------------------
class MhsTinyCanDriver:
    def __init__(self, dll=None, options=None):
        """
        Class Constructor
        @param dll: path to dll / shared library
        @param options: dictionary of options to be set
        @return: nothing
        """
        self.logger = uselogging.getLogger()
        self.Index = TIndex() #default FIFO Index 0
        self.UsedTxSlots = [] #for frequent messages, turns into a List of Indexes later
        self.UsedRxSlots = [] #for Can HW Filters, turns into a List of Indexes later
        self.Options = TCAN_Options
        self.TCDriverProperties = {}
        self.TCDeviceProperties = {}#no multidevice support yet
        if options:
            self.Options.update(options)
        self.so = None
        if dll:
            if sys.platform == "win32":
                self.so = WinDLL(dll)
            else:
                self.so = CDLL(dll)                            
        else:                        
            for sharedLibraryLocation in sharedLibraryLocations:
                try:
                    if sys.platform == "win32":
                        sharedLibrary = sharedLibraryLocation + os.sep + "mhstcan.dll"
                    else:
                        sharedLibrary = sharedLibraryLocation + os.sep + "libmhstcan.so"
                    self.logger.info('search library {0} in {1}'.format(sharedLibrary, sharedLibraryLocation))
                    if sys.platform == "win32":
                        self.so = WinDLL(sharedLibrary)
                    else:
                        self.so = CDLL(sharedLibrary)                    
                    self.logger.info('library found')
                    break
                except OSError:
                    self.logger.error('no valid library found')
                    pass
        if not self.so:
            raise RuntimeError('library not found: ' + sharedLibrary)
        err = self.initComplete(self.Index, self.Options)
        if err < 0:
            raise NotImplementedError('Device Init Failed')      

    # ----------------------------------------------------------------
    # --------------- Overall Init Function --------------------------
    # ----------------------------------------------------------------
    
    def initComplete(self,index, options=None, snr=None, canSpeed=None):
        """
        High Level Function to Load the DLL/Shared Library and Open the CAN Device and Start Up the CAN Bus
        @param options: Options Dictionary for Driver
        @param snr: Serial Number of Device
        @param can_bitrate: Bitrate / CAN Speed to be set       
        @return: Error Code (0 = No Error)
        """          
        self.logger.info('initComplete')
        #if Serial Number given use this device 
          
        if options and (type(options) == dict):
            UpdateOptionDict(self.Options,options,self.logger)            
        if snr:  
            UpdateOptionDict(self.Options,{'snr':snr},self.logger)  
        #obtain CAN Speed by prio explicite given parameter >> given option dictionary >> objects option dictionary
        if canSpeed:
            UpdateOptionDict(self.Options,{'canSpeed1':canSpeed},self.logger)
        #Init Cascade: Driver >> Device >> Options >> CAN BUS    
        err = self.initDriver(self.Options)
        if err >= 0:
            err = self.openDevice(index,options=self.Options)#[0]
        if err >= 0:
            err = self.setOptions(self.Options)
        if err >= 0:
            err = self.resetCanBus(index)
        if err >= 0:    
            self.logger.info('initComplete done (with success) for device with snr.: {0}'.format(snr))
        else:
            self.logger.info('init failed for device with snr.: {0}'.format(snr))
            self._CanDownDriver()
            self.so = None                 
        return err


    # ----------------------------------------------------------------
    # ----------------------------------------------------------------
    # ----------------------------------------------------------------


    # ----------------------------------------------------------------
    # ------ High Level Functions to interact with the Driver --------
    # ----------------------------------------------------------------

    def initDriver(self, options = None):
        """
        High Level Function to init the Driver - Wrapper Global Dictionary to OptionString  
        @param options: dictionary of options to be set
        @return: Error Code (0 = No Error)
        """        
        self.logger.info('initDriver')
        if options and (type(options) == dict):
            UpdateOptionDict(self.Options,options,self.logger)            
        OptionString = OptionDict2CsvString(OptionDict=self.Options,Keys=TCAN_Keys_CanInitDriver)
        err = self._CanInitDriver(OptionString)
        if err < 0:
            self.logger.error('initDriver Error-Code: {0}'.format(err))
            raise RuntimeError('Could not load Driver')
        self.TCDriverProperties.update(CsvString2OptionDict(self._CanDrvInfo()))
        return err
    
    def CanSetUpEvents(self,PnPEventCallbackfunc=None,StatusEventCallbackfunc=None,RxEventCallbackfunc=None):
        """
        High Level Function to Set Up Events
        @param PnPEventCallbackfunc: EventCallback in case of Plug and Play Event, e.g. someone has pulled out the cable
        @param StatusEventCallbackfunc: EventCallback in case of CAN Status Change, e.g. someone wrecked the can bus
        @param RxEventCallbackfunc: EventCallback in case of Message Receive, either filtered or not
        @return: Nothing
        """
        if not PnPEventCallbackfunc:
            PnPEventCallbackfunc = self.PnPEventCallback            
        err = self._CanSetPnPEventCallback(PnPEventCallbackfunc) #set PNP Callback Function
        if err:
            self.logger.error('Error while Setting PNP Callback')
        if not StatusEventCallbackfunc:
            StatusEventCallbackfunc = self.StatusEventCallback
        err = self._CanSetStatusEventCallback(StatusEventCallbackfunc)
        if err:
            self.logger.error('Error while Setting Status Event Callback')
        if not RxEventCallbackfunc:
            RxEventCallbackfunc = self.RxEventCallback
        err = self._CanSetRxEventCallback(RxEventCallbackfunc)
        if err:
            self.logger.error('Error while Setting Rx Event Callback')
        err = self.CanSetEvents(EVENT_ENABLE_ALL)
        if err:
            self.logger.error('Error while Enabling Event Callbacks')
        return



    # ----------------------------------------------------------------
    # ------ High Level Functions to interact with the Device --------
    # ----------------------------------------------------------------

    def openDevice(self, index=None, serial=None, options=None):
        """
        High Level Function to open a device
        @param serial: Serial Number of Device if you wish to override global Options
        @param options: dictionary of options to be set
        @return: Error Code (0 = No Error), index currently used
        @author: Patrick Menschel (menschel.p@posteo.de)
        @todo: Handle Exception if Serial Number is given but device is not found Handle in OPENDEVICE
        """
        self.logger.info('openDevice')
        if index == None:
            index = self.Index
        if options and (type(options) == dict):
            UpdateOptionDict(self.Options,options,self.logger)
        if serial:
            options.update({'snr':serial})
            UpdateOptionDict(self.Options,{'snr':serial},self.logger) 
        self.logger.info('CanDeviceClose prior to CanDeviceOpen')                                
        err = self._CanDeviceClose(index)
        if err < 0:
            self.logger.error('CanDeviceClose prior to CanDeviceOpen Error-Code: {0}'.format(err))
        err = self._CanDeviceOpen(index, OptionDict2CsvString(OptionDict=options,Keys=TCAN_Keys_CanDeviceOpen))
        if err < 0:
            self.logger.error('openDevice Error-Code: {0}'.format(err))
        self.TCDeviceProperties.update(CsvString2OptionDict(self._CanDrvHwInfo(index)))
        return err
    

    # ----------------------------------------------------------------
    # ------ High Level Functions to interact with the CAN Bus --------
    # ----------------------------------------------------------------

    def setOptions(self,options):
        """
        High Level Function to Set CAN Options
        @param options: dictionary of options to be set
        @return: Error Code (0 = No Error)
        """
        self.logger.info('setOptions')        
        if options and (type(options) == dict):
            UpdateOptionDict(self.Options,options,self.logger)        
        err = self._CanSetOptions(OptionDict2CsvString(OptionDict=options,Keys=TCAN_Keys_CanSetOption))
        if err < 0:
            self.logger.error('setOptions Error-Code: {0}'.format(err))
        return err
   
    def resetCanBus(self,index=None):
        """
        High Level Function to Reset the CAN Bus - basically get rid of the index for now
        @param index: Struct commonly used by the Tiny Can API 
        @return: Error Code (0 = No Error)
        @author: Patrick Menschel (menschel.p@posteo.de)
        """
        self.logger.info('resetCanBus')
        if index == None:
            index = self.Index
        err = self._CanReceiveClear(index)
        if err >= 0:
            err = self._CanTransmitClear(index)
        if err >= 0:
            err = self._CanSetMode(index, OP_CAN_START|OP_CAN_RESET, CAN_CMD_ALL_CLEAR)            
        return err
 
    def setCanBusSpeed(self,canSpeed,index=None):
        """
        High Level Function to Set the CAN Bus Speed - basically get rid of the index for now
        @param index: Struct commonly used by the Tiny Can API     
        @param canSpeed: Can Bitrate to be set 
        @return: Error Code (0 = No Error)
        @todo: handle custom bitrates here too later
        @author: Patrick Menschel (menschel.p@posteo.de)
        """
        if index == None:
            index = self.Index
        UpdateOptionDict(self.Options,{'canSpeed1':canSpeed},self.logger)
        return self._CanSetSpeed(index, canSpeed)
               
    def setCanMode(self,canMode,index=None):
        """
        High Level Function to Set the CAN Mode - basically get rid of the index for now
        @param index: Struct commonly used by the Tiny Can API     
        @param canMode: Mode to be set 
        @return: Error Code (0 = No Error)
        @author: Patrick Menschel (menschel.p@posteo.de)
        """
        if index == None:
            index = self.Index            
        return self._CanSetMode(index, canMode, 0)

    def setCanModeSilent(self,index=None):
        """
        High Level Function to Set the CAN Silent Mode
        @param index: Struct commonly used by the Tiny Can API     
        @param canMode: Mode to be set 
        @return: Error Code (0 = No Error)
        @author: Patrick Menschel (menschel.p@posteo.de)
        """
        if index == None:
            index = self.Index
        return self._CanSetMode(index, OP_CAN_START|OP_CAN_RESET|OP_CAN_LOM, 0)
    
    def clearCanErrors(self,index=None):
        if index==None:
            index = self.Index
        return self._CanSetMode(index,0,CAN_CMD_ALL_CLEAR)
        


    # ----------------------------------------------------------------
    # ---------------Event Handling Stuff ----------------------------
    # ----------------------------------------------------------------

    def PnPEventCallback(self,index,status):
        """
        Simple Plug and Play Event Handler to open the device again after reconnection and Print to STOUT
        @param index: Struct commonly used by the Tiny Can API
        @param status: simple Flag, 0 = disconnect, 1 = connect  
        @return: Nothing
        @author: Patrick Menschel (menschel.p@posteo.de)
        """
        self.logger.info('PnPEventCallback called with index {0} and status {1}'.format(index.Uint32,status))
        if status:
            self.CanDeviceOpen(index,self.Options)
            self.CanSetMode(index,OP_CAN_START, CAN_CMD_ALL_CLEAR)
            print('Device Connected')           
        else:
            print('Device Disconnected')
        return

    def StatusEventCallback(self,index,deviceStatusPointer):
        """
        Simple Callback for Status Change Event, Just Print Status to STDOUT
        @param index: Struct commonly used by the Tiny Can API
        @param deviceStatusPointer: Pointer to Device Status  
        @return: Nothing
        @author: Patrick Menschel (menschel.p@posteo.de)
        """
        print('Status Change Event for Index {0}'.format(index.Uint32))
        deviceStatus = deviceStatusPointer.contents
        #print('DeviceStatus: {0}'.format(deviceStatus))
        print(self.FormatCanDeviceStatus(deviceStatus.DrvStatus,deviceStatus.CanStatus,deviceStatus.FifoStatus))
        return

    def RxEventCallback(self,index,RxMessagePointer,count):
        """
        Simple Callback for CAN Rx Event, Just Print Message to STDOUT
        @param index: Struct commonly used by the Tiny Can API
        @param RxMessagePointer: Pointer to TCAN Message if DriverOption is set, NULL Pointer otherwise
        @param count: Number of Messages  
        @return: Nothing
        @author: Patrick Menschel (menschel.p@posteo.de)
        @todo: Check for counts > 1, Implement it, are they possible ?? 
        """
        if count > 1:
            raise NotImplementedError('RxEvent with more than 1 Message is not supported yet')
        if RxMessagePointer:
            RxMessage = RxMessagePointer.contents
            print("RxEvent from Index {0} with ID {1} Data: {2}  Count{3} ".format(index.Uint32,hex(RxMessage.Id),[hex(x) for x in RxMessage.Data],count))
        else:
            print("RxEvent from Index {0} with No Message attached".format(index.Uint32))
        return
    
    def CanSetEvents(self, events = EVENT_ENABLE_ALL):
        """
        Set Event Enable/Disable Bits for the Driver
        @param events: event mask to be set
        @return: Error Code (0 = No Error)
        @author: Patrick Menschel (menschel.p@posteo.de)
        @todo: change this to a dictionary
        """
        self.logger.info('CanSetEvents')
        err = self.so.CanSetEvents(c_ushort(events))
        if err < 0:
            self.logger.error('CanSetEvents Error-Code: {0}'.format(err))
        return err



        
    # ----------------------------------------------------------------
    # ----- Format and Printing Stuff for debugging purposes ---------
    # ----------------------------------------------------------------
    
    def CanReceiveAndFormatSimple(self, index, count=1):
        """
        High Level Function to Read a CAN Message
        @param index: Struct commonly used by the Tiny Can API
        @param count: Number of Messages to be read from FIFO
        @return: List of Strings containing formatted Messages
        """           
        formatedMessages = []
#         results = None       
        RxMessages = self._CanReceive(index, count)
        if RxMessages:
            for RxMessage in RxMessages:
                formatedMessage =  'ID:{0:08x}, DLC:{1},TxD:{2}, RTR:{3}, EFF:{4}, Source:{5}, Data:{6}'.format(RxMessage.Id,RxMessage.Flags.FlagBits.DLC,RxMessage.Flags.FlagBits.TxD,RxMessage.Flags.FlagBits.RTR,RxMessage.Flags.FlagBits.EFF,RxMessage.Flags.FlagBits.Source,[hex(x) for x in RxMessage.Data])
                formatedMessages.append(formatedMessage)
        return formatedMessages

    def FormatCanDeviceStatus(self,drv,can,fifo):
        """
        Simple Function to cast/format the Device Status to readable text by use of dictionaries
        @param drv: Driver Status
        @param can: Can Status
        @param fifo: Fifo Status 
        @return: A String to be printed for Information 
        @author: Patrick Menschel (menschel.p@posteo.de) 
        """        
        return 'Driver: {0}, CAN: {1}, Fifo: {2}'.format(DRIVER_STATUS_MODES[drv], CAN_STATUS_MODES[can], FIFO_STATUS_MODES[fifo])


    # --------------------------------------------------------------------
    # --------------- User Functions --- ---------------------------------
    # --------------------------------------------------------------------
     
    
    def TransmitData(self, msgId, msgData, index = None, rtr = None):
        """
        High Level Function to transmit a CAN Message
        @param index: Struct commonly used by the Tiny Can API, Drop the Index to select the FIFO      
        @param msgId: CAN ID of the Message
        @param msgData: Data of the Message
        @param rtr: Remote Transmission Request, Note: obsolete in any known CAN Protocol
        @return: Error Code (0 = No Error)    
        @todo: Return Code is 1 but no error  
        @author: Patrick Menschel (menschel.p@posteo.de) 
        """
        if index == None:
            index = self.Index
        if len(msgData) > 8:
            raise NotImplementedError('Messages with more then 8 Bytes are not yet supported')
#         Data = []
        Flags = TCANFlags()   
        self.logger.info('TransmitData')
        if type(msgData) != list:
            self.logger.error('List expected but got {0} instead'.format(type(msgData)))
            raise ValueError('List expected but got {0} instead'.format(type(msgData)))
        for i in msgData:
            if type(i) != int:
                self.logger.error('List of integers expected but got {0} in list instead'.format(type(i)))
                raise ValueError('List of integers expected but got {0} in list instead'.format(type(i)))      
        Flags.FlagBits.DLC = len(msgData)
        if rtr:
            Flags.FlagBits.RTR = 1
        Flags.FlagBits.TxD = 1
        if msgId > 0x7FF:
            Flags.FlagBits.EFF = 1
        err = self._CanTransmit(index, msgId, msgData, flags=Flags.Uint32) 
        if err < 0:
            self.logger.error('TransmitData Error-Code: {0}'.format(err))              
        return err   
        

    def SetInvervalMessage(self, msgId, msgData, interval, index = None, rtr = None):
        """
        High Level Function to transmit a CAN Message in given Interval
        @param index: Struct commonly used by the Tiny Can API        
        @param msgId: CAN ID of the Message
        @param msgData: Data of the Message
        @param interval: Interval in milliseconds, shared library operates in usec   
        @param rtr: Remote Transmission Request, Note: obsolete in any known CAN Protocol
        @return: Error Code (0 = No Error) 
        @author: Patrick Menschel (menschel.p@posteo.de)    
        """       
        self.logger.info('SetInvervalMessage') 
        if index:
            if type(index) == TIndex:
                IntervalIndex = index
            else:
                IntervalIndex.Uint32 = index
        else:
            IntervalIndex = self.GetFreeTxSlot()
            if not IntervalIndex:
                raise IndexError('No free TX Slot found.')
                    
        err = self._CanTransmitSet(index = IntervalIndex, flags=0x0, interval=interval)
        if err >= 0:
            err = self.TransmitData(msgId=msgId, msgData=msgData, index = IntervalIndex)
        if err >= 0:
            err = self._CanTransmitSet(index = IntervalIndex, flags=0x8001, interval=interval)
        if err < 0:
            self.logger.error('SetInvervalMessage Error-Code: {0}'.format(err))
        else:
            self.UsedTxSlots.append(IntervalIndex)
        return err,IntervalIndex      
        
    


    def SetFilter(self, msgId, msgMask, msgLen = None, index = None, rtr = None):
        """
        High Level Function to set a CAN Message Filter
        @param index: Struct commonly used by the Tiny Can API        
        @param msgId: CAN ID of the Message
        @param msgMask: BitMasks to bit and with the CAN ID to form the filter
        @param msgLen: Message Length to be filtered for
        @param rtr: Remote Transmission Request, Note: obsolete in any known CAN Protocol
        @return: Error Code (0 = No Error), TIndex under that the Filter was set 
        @author: Patrick Menschel (menschel.p@posteo.de)    
        """       
        self.logger.info('FilterSetUp')  
        filterIndex = TIndex()
        if index:
            if type(index) == TIndex:
                filterIndex = index
            else:
                filterIndex.Uint32 = index
        else:
            filterIndex = self.GetFreeRxSlot()
            if not filterIndex:
                raise IndexError('No free RX Slot found.')
            
        filterFlags = TMsgFilterFlags()
#         if msgId > 0x7FF:
#             filterFlags.FlagBits.EFF = 1 # Apparently this is not implemented at all in the Shared Library ?!
        if msgLen:
            filterFlags.FlagBits.DLC = msgLen
            filterFlags.FlagBits.DlcCheck = 1
        else:
            filterFlags.FlagBits.DLC = 0
            filterFlags.FlagBits.DlcCheck = 0
        if rtr:
            filterFlags.FlagBits.RTR = rtr
            
        filterFlags.FlagBits.DataCheck = 0 # No Options given        
        filterFlags.FlagBits.Mode = 0 #Drop Non Matching Messages as HW Filters do
        filterFlags.FlagBits.IdMode = 0 # Only do simple ID & MASK Filter        
        filterFlags.FlagBits.Type = 0 # No Options known        
        filterFlags.FlagBits.Enable = 1 # Enable by default
        
        err = self._CanSetFilter(index = filterIndex, code=msgId, mask=msgMask, flags=filterFlags.Uint32)
        if err < 0:
            self.logger.error('FilterSetUp Error-Code: {0}'.format(err))
        else:
            self.UsedRxSlots.append(filterIndex)
        return err,filterIndex



    def GetFreeRxSlot(self):
        """
        Helper Function to get a free Slot 
        @param None
        @return: Free Index of Type TIndex, None if none available
        @author: Patrick Menschel (menschel.p@posteo.de)    
        """   
        fslots = [s for s in range(1,self.TCDeviceProperties['Anzahl Filter']+1) if s not in [idx.IndexBits.SubIndex for idx in self.UsedRxSlots]]
        if fslots:
            NextFreeSlotIndex = TIndex()
            NextFreeSlotIndex.IndexBits.SubIndex = fslots[0]
            return NextFreeSlotIndex
        else:
            return None

    def GetFreeTxSlot(self):
        """
        Helper Function to get a free Slot 
        @param None
        @return: Free Index of Type TIndex, None if none available
        @author: Patrick Menschel (menschel.p@posteo.de)    
        """
        self.logger.info('GetFreeTxSlot')    
        fslots = [s for s in range(1,self.TCDeviceProperties['Anzahl Interval Puffer']+1) if s not in [idx.IndexBits.SubIndex for idx in self.UsedTxSlots]]
        if fslots:
            NextFreeSlotIndex = TIndex()
            NextFreeSlotIndex.IndexBits.SubIndex = fslots[0]
            return NextFreeSlotIndex
        else:
            return None  


    # ----------------------------------------------------------------
    # ---- API CALLS --------------------------- ---------------------
    # ----------------------------------------------------------------

    def _CanInitDriver(self, options = None):
        """
        API CALL - Constructor of the shared Library / DLL, Initialize the Tiny CAN API
        @param options: Option String - ByteString in Python3
        @return: Error Code (0 = No Error)
        """
        self.logger.info('CanInitDriver')
        self.logger.info('- with options = {0}'.format(options))
        err = self.so.CanInitDriver(c_char_p(options))
        if err < 0:
            self.logger.error('CanInitDriver Error-Code: {0}'.format(err))
        return err
            
    def _CanDownDriver(self):
        """
        API CALL - Destructor of the shared Library / DLL Shutdown the Tiny CAN API
        @return: Nothing
        """
        self.logger.info('CanDownDriver')
        self.so.CanDownDriver()
        return
    
    def _CanSetOptions(self, options = None):
        """
        API CALL - Set Options for the CAN Device
        @param options: Option String - ByteString in Python3
        @return: Error Code (0 = No Error)
        """
        self.logger.info('CanSetOptions')
        self.logger.info('- with options = {0}'.format(options))
        err = self.so.CanSetOptions(c_char_p(options))
        if err < 0:
            self.logger.error('CanSetOptions Error-Code: {0}'.format(err))
        return err
        
    def _CanDeviceOpen(self, index, options = None):
        """
        API CALL - Open a Can Device
        @param index: Struct commonly used by the Tiny CAN API
        @param options: Option String - ByteString in Python3
        @return: Error Code (0 = No Error) 
        """
        self.logger.info('CanDeviceOpen')
        self.logger.info('- with options = {0}'.format(options))
        err = self.so.CanDeviceOpen(c_ulong(index.Uint32), c_char_p(options))
        if err < 0:
            self.logger.error('CanDeviceOpen Error-Code: {0}'.format(err))
        return err
        
    def _CanDeviceClose(self, index):
        """
        API CALL - Close a CAN Device
        @param index: Struct commonly used by the Tiny Can API
        @return: Error Code (0 = No Error) 
        """
        self.logger.info('CanDeviceClose')
        err = self.so.CanDeviceClose(c_ulong(index.Uint32))
        if err < 0:
            self.logger.error('CanDeviceClose Error-Code: {0}'.format(err))
        return err
        
    def _CanSetMode (self, index, mode, flags):
        """
        API CALL - Set CAN Bus Mode of Operation
        @param index: Struct commonly used by the Tiny Can API
        @param mode: Mode of Can Operation, Start, Stop, Listen Only, No Auto Retransmission
        @param flags: Bitmask of flags to clear certain Errors, Filters,... 
        @return: Error Code (0 = No Error) 
        """
        self.logger.info('CanSetMode')
        err = self.so.CanSetMode(c_ulong(index.Uint32), c_ubyte(mode), c_ushort(flags)) 
        if err < 0:
            self.logger.error('CanSetMode Error-Code: {0}'.format(err))
        return err       
    
    def _CanTransmit(self, index, msgId, msgData, flags):
        """
        API CALL - Transmit a CAN Message
        @param index: Struct commonly used by the Tiny Can API        
        @param msgId: CAN ID of the Message
        @param msgData: Data of the Message, List of Integers
        @param flags: Flags to be set
        @return: Error Code (0 = No Error)      
        """    
        self.logger.info('CanTransmit')
        canMSG = TCanMsg()
        canMSG.Id = c_ulong(msgId)
        for i,b in enumerate(msgData):
                canMSG.Data[i] = b
        canMSG.Flags.Uint32 = flags
        err = self.so.CanTransmit(c_ulong(index.Uint32), pointer(canMSG), c_int(1))#transmit once
        if err < 0:
            self.logger.error('CanTransmit Error-Code: {0}'.format(err))
        return err
        
    def _CanTransmitClear(self, index):
        """
        API CALL - Clear the Transmit FIFO
        @param index: Struct commonly used by the Tiny Can API  
        @return: Error Code (0 = No Error)         
        """
        self.logger.info('CanTransmitClear')
        err = self.so.CanTransmitClear(c_ulong(index.Uint32))
        if err < 0:
            self.logger.error('CanTransmitClear Error-Code: {0}'.format(err))
        return err
        
    def _CanTransmitGetCount(self, index):
        """
        API CALL - Get Message Count currently in Transmit FIFO
        @param index: Struct commonly used by the Tiny Can API  
        @return: Number of Messages         
        """
        self.logger.info('CanTransmitGetCount')
        num = self.so.CanTransmitGetCount(c_ulong(index.Uint32))
        if num < 0:
            self.logger.error('CanTransmitGetCount Error-Code: {0}'.format(num))
        return num
        
    def _CanTransmitSet(self, index, flags, interval):
        """
        API CALL - Set the interval time for a CAN transmit message
        @param index: Struct commonly used by the Tiny Can API
        @param flags: BitMask of flags for certain tasks, Bit 0 =  Enable, Bit 15 = apply interval value
        @param interval: Interval in milliseconds, shared library operates in usec   
        @return: Error Code (0 = No Error)
        @todo: Return Code is 1 but no error           
        """
        self.logger.info('CanTransmitSet')
        usecs = int(interval*1000)
        err = self.so.CanTransmitSet(c_ulong(index.Uint32), c_ushort(flags), c_ulong(usecs))
        if err < 0:
            self.logger.error('CanTransmitSet Error-Code: {0}'.format(err))
        return err
            
    def _CanReceive(self, index, count=1):
        """
        API CALL - Read a CAN Message from FIFO or Buffer, depends on index
        @param index: Struct commonly used by the Tiny Can API
        @param count: Number of messages to be read 
        @return: CAN Messages of specified count or Error Code
        """        
        TCanMsgArrayType = TCanMsg * count # Struct of multiple TCANMsg Instances without using Python List object
        TCanMsgArray = TCanMsgArrayType()
        num = self.so.CanReceive(c_ulong(index.Uint32), pointer(TCanMsgArray), count)
        if num < 0:
            self.logger.info('CanReceive, Error-Code: {0}'.format(num))
            return num
        self.logger.info('CanReceive {0} message(s) received'.format(num))
        return TCanMsgArray
        
    def _CanReceiveClear(self, index):
        """
        API CALL - Clear a CAN Message FIFO or Buffer, depends on index
        @param index: Struct commonly used by the Tiny Can API 
        @return: Error Code (0 = No Error)
        """   
        self.logger.info('CanReceiveClear')
        err = self.so.CanReceiveClear(c_ulong(index.Uint32))
        if err  < 0:
            self.logger.error('CanReceiveClear Error-Code: {0}'.format(err))
        return err
        
    def _CanReceiveGetCount(self, index):
        """
        API CALL - Get Number of CAN Messages in FIFO or Buffer, depends on index
        @param index: Struct commonly used by the Tiny Can API 
        @return: Message Number or Error Code
        """  
        self.logger.info('CanReceiveGetCount')
        num = self.so.CanReceiveGetCount(c_ulong(index.Uint32))
        if num < 0:
            self.logger.error('CanReceiveGetCount Error-Code: {0}'.format(num))
        return num
        
    def _CanSetSpeed(self, index, speed):
        """
        API CALL - Set the Bitrate / Speed of the CAN BUS
        @param index: Struct commonly used by the Tiny Can API
        @param speed: Bitrate / speed 10 = 10kBit and so on 
        @return: Error Code (0 = No Error)
        """  
        self.logger.info('CanSetSpeed')
        err = self.so.CanSetSpeed(c_ulong(index.Uint32), c_ushort(speed))
        if err < 0:
            self.logger.error('CanSetSpeed Error-Code: {0}'.format(err))        
        return err
    
    def _CanSetFilter(self, index, mask, code, flags):
        """
        API CALL - Set a CAN Filter to a specific Index / SubIndex
        @param index: Struct commonly used by the Tiny Can API
        @param mask: Mask Bits that must apply bit-anded
        @param code: Message ID to be matched
        @param filter_Dlc: Length of Message to be checked for
        @param filter_Rtr: RTR Bit of Message, is there any use in it ?
        @param filter_Eff: Extended Format Flag, for 29bit 11bit comparasm, why isn't that handled automatically?
        @param filter_IdMode: Mode how Mask and Code are handled, leave at 0 for now as it's the most common method
        @param filter_DLCCheck: Flag to activate this Check
        @param filter_DataCheck: Flag to do something, What does this do ?
        @param filter_Mode: If or not Messages are destroyed that don't match the Filter
        @param filter_Enable: On/Off Switch for the Filter
        @return: Error Code (0 = No Error)
        """        
        canMSGFilter = TMsgFilter()
        canMSGFilter.Mask = mask
        canMSGFilter.Code = code
        canMSGFilter.Flags.Uint32 = flags
        err = self.so.CanSetFilter(c_ulong(index.Uint32), pointer(canMSGFilter))
        if err  < 0:
            self.logger.error('CanSetFilter Error-Code: {0}'.format(err))
        return int(err)
        
    def _CanDrvInfo(self):
        """
        API CALL - Get Driver Information from DLL / Shared Library
        @return: Version String of DLL / Shared Library
        """
        self.logger.info('CanDrvInfo')
        self.so.CanDrvInfo.restype = c_char_p
        return self.so.CanDrvInfo()
        
    def _CanDrvHwInfo(self, index):
        """
        API CALL - Get Firmware Information from Hardware Device
        @return: Version String of Hardware Device / Firmware
        """
        self.logger.info('CanDrvHwInfo')
        self.so.CanDrvHwInfo.restype = c_char_p
        return self.so.CanDrvHwInfo(c_ulong(index.Uint32))
        
    def _CanGetDeviceStatus(self, index):
        """
        API CALL - Get Device Status from Hardware Device / Firmware
        @return: Error Code, Driver Status, Can Status, Fifo Status       
        """
        self.logger.info('CanGetDeviceStatus')
        devSTAT = TDeviceStatus()
        err = self.so.CanGetDeviceStatus(c_ulong(index.Uint32), pointer(devSTAT))
        if err < 0:
            self.logger.error('CanGetDeviceStatus Error-Code: {0}'.format(err))
        return err,devSTAT.DrvStatus,devSTAT.CanStatus,devSTAT.FifoStatus

    def _CanSetPnPEventCallback(self,CallbackFunc=None):
        """
        API CALL - Set the Callback Event Function for the Plug and Play Event aka Plug In/ Pull Out of Device
        @param CallbackFunc: The Function to call in case of PNP Event
        @requires: The Function specified by Callback must provide the Parameters that the Callback specifies
        @return: Error Code (0 = No Error)
        @author: Patrick Menschel (menschel.p@posteo.de)
        @todo: Find out why the Callback on Linux does not work for Device connect but on Windows for Connect and Disconnect even if Driver Option is not set
        """
        self.logger.info('CanSetPnpEventCallback')
        if sys.platform == "win32":
            PNPCALLBACKFUNC = WINFUNCTYPE(None, TIndex, c_ulong) # CallbackFunction Prototype for PNP Callback using CFUNCTYPE(ReturnValue, Argument1, Argument2,...)
            
        else:
            PNPCALLBACKFUNC = CFUNCTYPE(None, TIndex, c_ulong) # CallbackFunction Prototype for PNP Callback using CFUNCTYPE(ReturnValue, Argument1, Argument2,...)            
        self.PNPCallBack = PNPCALLBACKFUNC(CallbackFunc)
        err = self.so.CanSetPnPEventCallback(self.PNPCallBack)
        if err < 0:
            self.logger.error('CanSetPnPEventCallback with Function {0} raised Error Code {1}'.format(CallbackFunc,err))
        return err
        
    def _CanSetStatusEventCallback(self,CallbackFunc = None):
        """
        API CALL - Set the Callback Event Function for the Status Event aka Bus Off etc.
        @param CallbackFunc: The Function to call in case of Status Event
        @requires: The Function specified by Callback must provide the Parameters that the Callback specifies
        @return: Error Code (0 = No Error)
        @author: Patrick Menschel (menschel.p@posteo.de)
        """
        self.logger.info('CanSetStatusEventCallback')
        if sys.platform == "win32":
            STATUSEVENTCALLBACKFUNC = WINFUNCTYPE(None, TIndex, POINTER(TDeviceStatus)) # CallbackFunction Prototype for Status Event Callback using CFUNCTYPE(ReturnValue, Argument1, Argument2,...)
        else:
            STATUSEVENTCALLBACKFUNC = CFUNCTYPE(None, TIndex, POINTER(TDeviceStatus)) # CallbackFunction Prototype for Status Event Callback using CFUNCTYPE(ReturnValue, Argument1, Argument2,...)
        self.StatusEventCallBack = STATUSEVENTCALLBACKFUNC(CallbackFunc)
        err = self.so.CanSetStatusEventCallback(self.StatusEventCallBack)
        if err < 0:
            self.logger.error('CanSetStatusEventCallback with Function {0} raised Error Code {1}'.format(CallbackFunc,err))
        return err           
    
    def _CanSetRxEventCallback(self, CallbackFunc = None):
        """
        API CALL - Set the Callback Event Function for the CAN Rx Event
        @param CallbackFunc: The Function to call in case of Can Rx Event
        @requires: The Function specified by Callback must provide the Parameters that the Callback specifies
        @return: Error Code (0 = No Error)
        @author: Patrick Menschel (menschel.p@posteo.de)
        """
        self.logger.info('CanSetRxEventCallback')
        if sys.platform == "win32":
            RXEVENTCALLBACKFUNC = WINFUNCTYPE(None, TIndex, POINTER(TCanMsg),c_ulong) # CallbackFunction Prototype for Rx Event Callback using CFUNCTYPE(ReturnValue, Argument1, Argument2,...)
            
        else:
            RXEVENTCALLBACKFUNC = CFUNCTYPE(None, TIndex, POINTER(TCanMsg),c_ulong) # CallbackFunction Prototype for Rx Event Callback using CFUNCTYPE(ReturnValue, Argument1, Argument2,...)
            
        self.RxEventCallBack = RXEVENTCALLBACKFUNC(CallbackFunc)
        err = self.so.CanSetRxEventCallback(self.RxEventCallBack)
        if err < 0:
            self.logger.error('CanSetRxEventCallback with Function {0} raised Error Code {1}'.format(CallbackFunc,err))
        return err
  
    
    # ----------------------------------------------------------------
    # --------------- End of API Calls--- ----------------------------
    # ----------------------------------------------------------------
    
    
 

        
# --------------------------------------------------------------------
# --------------------------------------------------------------------
# --------------------------------------------------------------------
if __name__ == '__main__':

    import random
    from baseOptionParser import BaseOptionParser


    # options parser
    # --------------
    usage = "usage: %prog [options]"
    parser = BaseOptionParser(usage, version=VERSION, addPollingTime=True)

    parser.add_option("-S", action="store", type="string", dest="snr", metavar="SNR",
                      help="serial number of the device", default=None)

    parser.add_option("-b", action="store", type="int", dest="bitrate", metavar="KBIT",
                      help="can bitrate in kBit/s, default = 250", default=250)

    parser.add_option("-m", action="store", type="string", dest="testmode", metavar="TESTMODE",
                      help="testing mode:" + \
                           "1=send only, 2=receive only, 3=loop back, 4=send and receive, 5=events, 6=filter", default=1)


    (options, args) = parser.parse_args()
    if args:
        parser.error("incorrect number of arguments")
    if options.polltime < 0.01:
        parser.error("polltime to short (must be greater than 0.01s")

    if options.bitrate not in canBitrates:
        parser.error("invalid can bitrate")
    bitrate = options.bitrate

    testmodes = {
        '1': 'sendOnly',
        '2': 'receiveOnly',
        '3': 'loopBack',
        '4': 'sendAndReceive',
        '5': 'events',
        '6': 'filter'}

    testmode = testmodes['6']
    if options.testmode in testmodes:
        testmode = testmodes[options.testmode]

    polltime = options.polltime
    snr = options.snr

    # start message
    print (VERSION)

    # create the driver
    canDriver = MhsTinyCanDriver(0,options = {'CanRxDMode':1,
                                            'AutoConnect':1,
                                            'CanSpeed1':250})
    
    import pprint
    print('Driver Dict follows:')
    pprint.pprint(canDriver.TCDriverProperties)
    print('Device Dict follows:')
        
    pprint.pprint(canDriver.TCDeviceProperties)
    # device status
    print ('ready to start')
    status = canDriver._CanGetDeviceStatus(canDriver.Index)
    print(canDriver.FormatCanDeviceStatus(status[1],status[2],status[3]))


    # do test mode forever
    try:
        if testmode == 'receiveOnly':
            print ('start', testmode)

            filterNumber = 1
            mask = 0x0001
            code = 0x0001
            result = canDriver.CanSetFilter(filterNumber, mask, code, \
                                            filter_Dlc=0,
                                            filter_Rtr=0,
                                            filter_Eff=1,
                                            filter_IdMode=0,
                                            filter_DLCCheck=0,
                                            filter_DataCheck=0,
                                            filter_SinglePuffer=0,
                                            filter_Mode=0,
                                            filter_Enable=1)

            print ('set filter result is: {0}'.format(result))
            while True:
                time.sleep(polltime)
                NumOfRxMsgs = canDriver.CanReceiveGetCount(canDriver.Index)
                if NumOfRxMsgs > 0:
                    RxMsgs = canDriver.CanReceiveAndFormatSimple(canDriver.Index, count=NumOfRxMsgs)
                    for RxMsg in RxMsgs:
                        print(RxMsgs)
        elif testmode == 'loopBack':
            print ('start', testmode)
            numNotReceived = 0
            debugHistory = ''
            while True:
                time.sleep(polltime)
                debugHistory += 'a'
                results = canDriver.CanReceive(canDriver.Index, count=6)
                debugHistory += 'b'
                if results:
                    numNotReceived = 0
                    debugHistory += 'c'
                    canDriver.CanTransmitClear(canDriver.Index)
                    canDriver.CanTransmit(canDriver.Index, msgId=results[0][0], flags = results[0][1], msgData = results[0][2:])
                    debugHistory += 'd-'
                    if len(debugHistory) > 80:  debugHistory = ''
                else:
                    numNotReceived += 1
                    if numNotReceived > 50:
                        debugHistory += 'x'
                        err = canDriver.CanInitDriver()
                        if not err:
                            err = canDriver.openDevice()
                            if not err:
                                err = canDriver.initCanBus(bitrate)
                        print ('>>> device {0} assigned'.format(canDriver.device))
                        if err:
                            debugHistory += 'z-'
                        else:
                            debugHistory += 'y-'
                        print ('Reset-History:', debugHistory)

                        debugHistory = ''
                        numNotReceived = 0
                    else:
                        debugHistory += 'f-'

        elif testmode == 'sendAndReceive':
            print ('start', testmode)

            counter = 0
            rxErrors = 0
            timeoutErrors = 0
            while True:
                time.sleep(polltime)
                pattern = [1, 8, 0, 0, 0, 0, 0, 0, 0, 0]
                for i in range(8):
                    pattern[i+2] = random.randint(10,99)
                canDriver.CanTransmit(canDriver.Index, msgId = pattern[0], flags = pattern[1], msgData = pattern[2:])
                time.sleep(0.100) #the loopback is not that fast...
                results = None
                waitAnswer = 50
                while waitAnswer:
                    results = canDriver.CanReceive(0, count=1)
                    if results: break
                    time.sleep(0.05)
                    waitAnswer -= 1
                if not results:
                    print ("no answer")
                    timeoutErrors += 1
                else:
                    print ('pattern =', pattern)
                    print ('result  =', results[0])
                    if results[0] != pattern:
                        rxErrors += 1
                counter += 1
                print ('count={0}, timeouts={1}, errors={2}'.format(counter, timeoutErrors, rxErrors))

        elif testmode == 'sendOnly':
            print ('start', testmode)
            idCounter = 0
            while True:
                pattern = [idCounter, 0x88, 0, 0, 0, 0, 0, 0, 0, 0]
                for i in range(8):
                    pattern[i+2] = random.randint(10,99)
                print ('message sending: {0} {1}'.format(hex(pattern[0]), [hex(p) for p in pattern[1:]]))
                err = canDriver.TransmitData(msgId = pattern[0], msgData = pattern[2:])

                if err < 0:
                    print('Error while sending Message - Getting Device Status')
                    status = canDriver.CanGetDeviceStatus(0)
                    print(canDriver.FormatCanDeviceStatus(status[1],status[2],status[3]))
                    print('Resetting CAN')
                    canDriver.CanSetMode(canDriver.Index, OP_CAN_RESET, 0) 
                idCounter += 1
                time.sleep(polltime)
        elif testmode == 'events':
            print('Set up Events')
            canDriver.CanSetUpEvents()
            while True:
                print('Sending Hello as Integers on ID 0x612')
                err = canDriver.TransmitData(msgId = 0x610, msgData = [ord(x) for x in "Hello"])
                time.sleep(polltime)
        elif testmode == 'filter':
            myFilterMask = 0x1FFFFFFF
            myFilterID = 0x18FFDA00
            for i in range(canDriver.TCDeviceProperties['Anzahl Filter']):
                err,myFilterIndex = canDriver.SetFilter(myFilterID+i, myFilterMask)            
                print('Set up Filter to Index {0} with ID {1} and Mask {2}, Error: {3}'.format(hex(myFilterIndex.Uint32),hex(myFilterID),hex(myFilterMask),err))
                myFilterID += 1
            canDriver.CanSetEvents(EVENT_ENABLE_PNP_CHANGE|EVENT_ENABLE_RX_FILTER_MESSAGES|EVENT_ENABLE_STATUS_CHANGE)  
            myIntervalID = 0x18FF00DA 
            myIntervalInterval = 1000
            for i in range(canDriver.TCDeviceProperties['Anzahl Interval Puffer']):                           
                err,myIntervalIndex = canDriver.SetInvervalMessage(msgId = myIntervalID, msgData = [ord(x) for x in "Hello"], interval = myIntervalInterval)
                print('Set up Interval Message to Index {0} with ID {1} and Interval {2}ms, Error: {3}'.format(hex(myIntervalIndex.Uint32),hex(myIntervalID),myIntervalInterval,err))
                myIntervalID += 0x100
                myIntervalInterval += 500                      
            while True:
                print('Polling Rx FIFO - Filter')
                myFilterCount = canDriver._CanReceiveGetCount(canDriver.Index)
                print('{0} Messages in FiFO'.format(myFilterCount))
                if myFilterCount:
                    print(canDriver.CanReceiveAndFormatSimple(canDriver.Index,count = myFilterCount))                                       
                time.sleep(polltime)    
    except KeyboardInterrupt:
        pass

    # shutdown
    canDriver.resetCanBus()
    canDriver._CanDownDriver()
    canDriver.so = None
    print ('done')
