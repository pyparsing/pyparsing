import pyparsing
from string import rstrip
import pprint
import pdb

# helpers for common text structures
def _label( str, delim=None ):
  if delim:
    return ( pyparsing.Literal( str ) + pyparsing.Literal( delim ) ).suppress()
  else:
    return pyparsing.Literal( str ).suppress()

_vert  = pyparsing.Literal("|").suppress()

def _tableRow( tokenlist, asList = False ):
  row = pyparsing.And( [ _vert ] )
  for t in tokenlist:
    row.append( t )
    row.append( _vert )
  
  #~ print row.exprs
  if asList:
    return pyparsing.Group( row )
  else:
    return row

def wrapPrint(s,wid=60):
    return "\n".join([ s[i*wid:i*wid+wid] for i in range(len(s)/wid+1) ])
        
# parse action helpers for converting parsed strings to native data types
def _tokensToFloat( str, loc, toks ):
  return map( float, toks )

def _tokensToInt( str, loc, toks ):
  return map( int, toks )
  
def _tokensToBool( str, loc, toks ):
  ynToBool = lambda yn : yn == "Y"
  return map( ynToBool, toks )

def _tokenTrim( str, loc, toks ):
  return map( rstrip, toks )

def waferIdLabel( str, loc, toks ):
    return [ "WFR%02d" % int(toks[0]) ]
    
def xmlTagSafe( str, loc, toks ):
    return [ "".join( [c for c in toks[0] if c in pyparsing.alphanums+"_" ] ) ]


def BNF():

  # define basic token building blocks
  colon = pyparsing.Literal(":")
  slash = pyparsing.Literal("/")
  point = pyparsing.Literal(".")
  
  wordchars = pyparsing.alphanums + "_/*&^%$#@!-=+.,?"
  word = pyparsing.Word( wordchars )
  tagword = pyparsing.Word( wordchars ).setParseAction( xmlTagSafe )
  restofline = pyparsing.Word( pyparsing.printables + " " ).setParseAction( _tokenTrim )
  
  number = pyparsing.Word( pyparsing.nums ).setName( "number" )
  integer = pyparsing.Word( pyparsing.nums+"+-", pyparsing.nums ).setParseAction( _tokensToInt ).setName("int")
  fnumber = pyparsing.Combine( pyparsing.Word( pyparsing.nums+"-", pyparsing.nums ) + point + number ).setName("float").setParseAction( _tokensToFloat )
  waferId = pyparsing.Word( pyparsing.nums ).setParseAction( waferIdLabel ).setName("waferId")

  date = pyparsing.Combine( number + slash + number + slash + number )
  hhmm = pyparsing.Combine( number + colon + number )
  hhmmss = pyparsing.Combine( number + colon + number + colon + number )
  
  yn   = pyparsing.Word("YNyn", max=1).setParseAction( _tokensToBool )

  #
  # start defining major file sections
  #

  """
  Operator:CCC    Machine:6911    Release:8.3.0    Date:03/26/2001  Time:11:37
  
  
  Batch Type                   : Production               
  Batch ID                     : 24141506       
  Job Name                     : PHS04/P5107RM59                         
  Layer ID                     : 399A1457N1       Layer Number :     1
  Combined zero/first Layer    : N
  Combined Mark/Image Exposure : N
  Control Mode                 : Cassettes        Batch Size   :     1
  """
  hdr = _label("Operator",":") + word.setResultsName("operator") + \
        _label("Machine",":") + word.setResultsName("machine") + \
        _label("Release",":") + pyparsing.delimitedList( number, ".", combine=True).setResultsName("sfwVersion") +\
        _label("Date",":") + date.setResultsName("date") + \
        _label("Time",":") + hhmm.setResultsName("time")
  
  batchDataHdr = \
        _label("Batch Type",":") + word.setResultsName("batchType") + \
        _label("Batch ID",":") + word.setResultsName("batchId") + \
        _label("Job Name",":") + word.setResultsName("jobName") + \
        pyparsing.Optional( _label("Job Modified",":") + date + hhmmss ) + \
        _label("Layer ID",":") + word + _label("Layer Number",":") + integer + \
        pyparsing.Optional( _label("Combined zero/first Layer",":") + yn ) + \
        _label("Combined Mark/Image Exposure",":") + yn + \
        _label("Control Mode",":") + word + pyparsing.Optional( _label("Batch Size",":") + integer )
        
  """
  PROCESS DATA
  
  +-----------------+--------------+----------+------------------------+
  |                 |              |          |         Focus          |
  |                 |              |          +--------+---------------+
  |                 |              |  Energy  | Offset |     Tilt      |
  |                 |              +----------+--------+-------+-------+
  |    Image ID     |  Reticle ID  |  Actual  |Nominal |  Rx   |  Ry   |
  |                 |              | [mJ/cm2] |  [um]  |[urad] |[urad] |
  +=================+==============+==========+========+=======+=======+
  | MAINCHIP        | 5107D1457N1  |     23.0 |  -0.05 |   0.0 |   0.0 |
  +-----------------+--------------+----------+--------+-------+-------+ 
  
  PROCESS DATA (CONTINUED)
  
  +-----------------+------+-----------------+---------+-----------------+
  |                 | Ill. |                 |Numerical|      Sigma      |
  |                 +------+                 +---------+--------+--------+
  |    Image ID     | Mode |  Quadrupole ID  |Aperture | Outer  | Inner  |
  +=================+======+=================+=========+========+========+
  | MAINCHIP        | C    | Not Applicable  |   0.55  |  0.400 |  0.000 |
  +-----------------+------+-----------------+---------+--------+--------+
  """
  processData1 = \
        _label("PROCESS DATA") + \
        _label("+-----------------+--------------+----------+------------------------+") + \
        _label("|                 |              |          |         Focus          |") + \
        _label("|                 |              |          +--------+---------------+") + \
        _label("|                 |              |  Energy  | Offset |     Tilt      |") + \
        _label("|                 |              +----------+--------+-------+-------+") + \
        _label("|    Image ID     |  Reticle ID  |  Actual  |Nominal |  Rx   |  Ry   |") + \
        _label("|                 |              | [mJ/cm2] |  [um]  |[urad] |[urad] |") + \
        _label("+=================+==============+==========+========+=======+=======+") + \
        _tableRow( ( word, word, fnumber, fnumber, fnumber , fnumber ) ) + \
        _label("+-----------------+--------------+----------+--------+-------+-------+")
  processData2 = \
        _label("PROCESS DATA") + \
        _label("+-----------------+--------------+----------+--------------------------+") + \
        _label("|                 |              |          |          Focus           |") + \
        _label("|                 |              |          +--------+-----------------+") + \
        _label("|                 |              |  Energy  | Offset |      Tilt       |") + \
        _label("|                 |              +----------+--------+--------+--------+") + \
        _label("|    Image ID     |  Reticle ID  |  Actual  |Nominal |   Rx   |   Ry   |") + \
        _label("|                 |              | [mJ/cm2] |  [um]  | [urad] | [urad] |") + \
        _label("+=================+==============+==========+========+========+========+") + \
        _tableRow( ( word, word, fnumber, fnumber, fnumber , fnumber ) ) + \
        _label("+-----------------+--------------+----------+--------+--------+--------+")
        
  processDataContd = \
        _label("PROCESS DATA (CONTINUED)") + \
        _label("+-----------------+------+-----------------+---------+-----------------+") + \
        _label("|                 | Ill. |                 |Numerical|      Sigma      |") + \
        _label("|                 +------+                 +---------+--------+--------+") + \
        _label("|    Image ID     | Mode |  Quadrupole ID  |Aperture | Outer  | Inner  |") + \
        _label("+=================+======+=================+=========+========+========+") + \
        _tableRow( ( word, word , ( pyparsing.Literal("Not Applicable") | word ), fnumber, fnumber , fnumber ) ) + \
        _label("+-----------------+------+-----------------+---------+--------+--------+")

  """
  EXPOSURE DATA

  +-----------------+-----------+----------+--------------------------+
  |                 | Exposure  |          |          Focus           |
  |                 +-----+-----+          +--------+--------+--------+
  |    Image ID     | Col | Row |  Energy  | Offset |   Rx   |   Ry   |
  |                 |     |     | [mJ/cm2] |  [um]  | [urad] | [urad] |
  +=================+=====+=====+==========+========+========+========+
  | PRIMARY         |  -3 |  -3 |    23.10 |  -0.05 |    0.0 |    0.0 |
  +-----------------+-----+-----+----------+--------+--------+--------+
  """
  exposureData = \
        _label("EXPOSURE DATA") + \
        _label("+-----------------+-----------+----------+--------------------------+") + \
        _label("|                 | Exposure  |          |          Focus           |") + \
        _label("|                 +-----+-----+          +--------+--------+--------+") + \
        _label("|    Image ID     | Col | Row |  Energy  | Offset |   Rx   |   Ry   |") + \
        _label("|                 |     |     | [mJ/cm2] |  [um]  | [urad] | [urad] |") + \
        _label("+=================+=====+=====+==========+========+========+========+") + \
        pyparsing.OneOrMore( _tableRow( ( pyparsing.Optional(word), integer, integer, fnumber, fnumber, fnumber, fnumber ) ) ) + \
        _label("+-----------------+-----+-----+----------+--------+--------+--------+")

  explanationLabel = \
        _label("Explanation: The Illumination Modes (Ill. Mode) are:") + \
                _label("A=Annular, C=Conventional, D=Default, Q=Quadrupole") + \
                _label("D(A)=Default Annular, D(C)=Default Conventional")

  """
  BATCH DATA

  Error Handling
    Operator Intervention                   : N
    Maximum Focus Error Count               :   0
    Maximum Dynamic Performance Error Count :   0
  
  Machine Clearance
    Reticles           : Y         Wafers            : Y
  
  Track Interface Usage
    Track Input Used   : Y         Track Output Used : Y

  Machine Clearance
    Reticles           : Y         Wafers            : Y
  
  Track Interface Usage
    Track Input Used   : Y         Track Output Used : Y
  
  Elevator Usage
    Elevator 1         : Reject  
    Elevator 2         : Not Used
    Elevator 3         : Not Used
    Elevator 4         : Not Used
  
  Cassette Integrity   : None   
  
  Alignment
    Wafer Alignment Method      : TTL
  
    Optical Prealignment     : Default    Prealignment Recovery : None       
    Number of Marks Required :         2
  
  Alignment Criteria
    Minimum Mark Distance           [%] :   40
    Maximum delta 8.0 to 8.8 Shift [um] :    0.500
    Maximum Model Residue          [nm] :  200.0
    SPM Mark Scan                       : Small 
    Wafer Grid Correction               : Default              
    88 and 8 um Error Detection         : Machine Dependent
  
  Lens Heating Correction               :    1.00
  """
  
  batchData = \
        _label("BATCH DATA") + \
        _label("Error Handling") + \
        _label("Operator Intervention", ":") + word + \
        _label("Maximum Focus Error Count", ":") + integer + \
        pyparsing.Optional( _label("Maximum Dynamic Performance Error Count", ":") + integer ) + \
        _label("Machine Clearance") + \
        _label("Reticles", ":") + yn + \
        _label("Wafers", ":") + yn + \
        _label("Track Interface Usage") + \
        _label("Track Input Used", ":") + yn.setResultsName("trackInputUsed") + \
        _label("Track Output Used", ":") + yn.setResultsName("trackOutputUsed") + \
        _label("Elevator Usage") + \
        _label("Elevator 1",":") + restofline + \
        _label("Elevator 2",":") + restofline + \
        _label("Elevator 3",":") + restofline + \
        _label("Elevator 4",":") + restofline + \
        _label("Cassette Integrity",":") + word + \
        _label("Alignment") + \
        pyparsing.Optional( _label("Wafer Alignment Method",":") + word ) + \
        pyparsing.Optional( _label("Matching Set ID",":") + restofline ) + \
        _label("Optical Prealignment",":") + word + \
        _label("Prealignment Recovery",":") + word + \
        _label("Number of Marks Required",":") + integer + \
        _label("Alignment Criteria") + \
        _label("Minimum Mark Distance           [%]",":") + integer + \
        _label("Maximum delta 8.0 to 8.8 Shift [um]",":") + fnumber.setResultsName("maxDelta") + \
        _label("Maximum Model Residue          [nm]",":") + fnumber + \
        _label("SPM Mark Scan",":") + restofline + \
        _label("Wafer Grid Correction",":") + restofline + \
        pyparsing.Optional( _label("88 and 8 um Error Detection",":") + restofline ) + \
        _label("Lens Heating Correction",":") + fnumber + \
        pyparsing.Optional( _label("Optimise Level Performance",":") + yn )
  
  """
  PROCESS CORRECTIONS    ASML Defaults
  
  Interfield Corrections
    Translation [um]  X            :      0.000  Y :      0.000
    Rotation                [urad] :      0.00
    Non-orthogonality       [urad] :      0.00
    Expansion [ppm]   X            :      0.000  Y :      0.000
  
  Intrafield Corrections
    Translation [um]  X            :      0.000  Y :      0.000
    Rotation                [urad] :      0.00
    Magnification            [ppm] :      0.00
    Asymmetric Rotation     [urad] :      0.00
    Asymmetric Magnification [ppm] :      0.00
  
  Prealignment Corrections
    Translation [mm]  X            :      0.000  Y :      0.000
    Rotation                [mrad] :      0.000
  
  Wafer Rotation             [deg] :      0.00
  
  8.0 to 8.8 Shift Corrections
    M1 [um]           X            :      0.000  Y :      0.000
    M2 [um]           X            :      0.000  Y :      0.000
  """
  processCorrections = \
        _label("PROCESS CORRECTIONS    ASML Defaults") +  \
        _label("Interfield Corrections") +  \
        _label("Translation [um]") + \
        _label("X",":") + fnumber + _label("Y",":") + fnumber + \
        _label("Rotation                [urad]",":") + fnumber + \
        _label("Non-orthogonality       [urad]",":") + fnumber + \
        _label("Expansion [ppm]") + \
        _label("X",":") + fnumber + _label("Y",":") + fnumber + \
        _label("Intrafield Corrections") +  \
        _label("Translation [um]") + \
        _label("X",":") + fnumber + _label("Y",":") + fnumber + \
        _label("Rotation                [urad]",":") + fnumber + \
        _label("Magnification            [ppm]",":") + fnumber + \
        pyparsing.Optional( _label("Asymmetric Rotation     [urad]",":") + fnumber ) + \
        pyparsing.Optional( _label("Asymmetric Magnification [ppm]",":") + fnumber ) + \
        _label("Prealignment Corrections") +  \
        _label("Translation [mm]") + \
        _label("X",":") + fnumber + _label("Y",":") + fnumber + \
        _label("Rotation                [mrad]",":") + fnumber + \
        _label("Wafer Rotation             [deg]",":") + fnumber + \
        _label("8.0 to 8.8 Shift Corrections") + \
        _label("M1 [um]") + \
        _label("X",":") + fnumber + _label("Y",":") + fnumber + \
        _label("M2 [um]") + \
        _label("X",":") + fnumber + _label("Y",":") + fnumber + \
        pyparsing.Optional( _label("Levelling Mode")  + \
                          _label("Critical Percentage [%]",":") + integer )    
  """
  BATCH MONITORING DATA
  
  Batch started at           : 03/26/2001 11:34:30
  Remaining Lightsource Time : 001:10
  Used Lightsource Time      : 10055:49
  
  Batch finished at          : 03/26/2001 11:37:14
  No. of Wafers out Batch    :     1
  No. of Wafers Accepted     :     1
  No. of Wafers Rejected     :     0
  Remaining Lightsource Time : 001:08
  Used Lightsource Time      : 10055:49
  """
  batchMonitoringData = \
        _label("BATCH MONITORING DATA") + \
        _label("Batch started at",":") + date + hhmmss + \
        _label("Remaining Lightsource Time",":") + hhmm + \
        _label("Used Lightsource Time",":") + hhmm + \
        _label("Batch finished at",":") + date + hhmmss + \
        _label("No. of Wafers out Batch",":") + integer + \
        _label("No. of Wafers Accepted",":") + integer + \
        _label("No. of Wafers Rejected",":") + integer + \
        _label("Remaining Lightsource Time",":") + hhmm + \
        _label("Used Lightsource Time",":") + hhmm


  """
  IMAGE DATA
  
  +-----------------+-------------------------+
  |                 |                         |
  |    Image ID     |     Exposure Route      |
  |                 |                         |
  +=================+=========================+
  | PRIMARY         | Optimised               |
  +-----------------+-------------------------+
  """
  imageData = \
        _label("IMAGE DATA") + \
        _label("+-----------------+-------------------------+") + \
        _label("|                 |                         |") + \
        _label("|    Image ID     |     Exposure Route      |") + \
        _label("|                 |                         |") + \
        _label("+=================+=========================+") + \
        _tableRow( ( word, word ) ) + \
        _label("+-----------------+-------------------------+")

  """
  WAFER DATA
  
  +-------+---------+----------+-------+---------+---------------------+
  |       |         |          |       |         |Wafer Processing Time|
  |       |         |          |       |         +----------+----------+
  | Wafer | Status  | Exposed  |   T   |    P    |  Begin   |   End    |
  |       |         |          |[degC] | [mbar]  |          |          |
  +=======+=========+==========+=======+=========+==========+==========+
  |     1 | Accept  | Complete |  22.0 |  1002.0 | 11:35:25 | 11:37:05 |
  +-------+---------+----------+-------+---------+----------+----------+
  """
  waferData1 = \
        _label("WAFER DATA") + \
        _label("+-------+---------+----------+-------+---------+---------------------+") + \
        _label("|       |         |          |       |         |Wafer Processing Time|") + \
        _label("|       |         |          |       |         +----------+----------+") + \
        _label("| Wafer | Status  | Exposed  |   T   |    P    |  Begin   |   End    |") + \
        _label("|       |         |          |[degC] | [mbar]  |          |          |") + \
        _label("+=======+=========+==========+=======+=========+==========+==========+") + \
        pyparsing.OneOrMore( _tableRow( ( waferId.setResultsName("wafernum"), word, word, fnumber, fnumber, hhmmss.setResultsName("procBegin"), hhmmss.setResultsName("procEnd") ), asList=True ) ) + \
        _label("+-------+---------+----------+-------+---------+----------+----------+")

  waferData2 = \
        _label("WAFER DATA") + \
        _label("+-------+---------+----------+---------+----------+---------------------+") + \
        _label("|       |         |          |         |          |Wafer Processing Time|") + \
        _label("|       |         |          |         |          +----------+----------+") + \
        _label("| Wafer | Status  | Exposed  |    T    |    P     |  Begin   |   End    |") + \
        _label("|       |         |          | [degC]  |  [mbar]  |          |          |") + \
        _label("+=======+=========+==========+=========+==========+==========+==========+") + \
        pyparsing.OneOrMore( _tableRow( ( waferId.setResultsName("wafernum"), word, word, fnumber, fnumber, hhmmss.setResultsName("procBegin"), hhmmss.setResultsName("procEnd") ), asList=True ) ) + \
        _label("+-------+---------+----------+---------+----------+----------+----------+")
  
  """
  ERRORS
  
  +-------+--------------+------+------+-----------------+
  |       |  Alignment   |Focus | Dyn  |                 |
  |       +------+-------+------+------+                 |
  | Wafer | Pre  |Global |#Errs |#Errs |     Others      |
  +=======+======+=======+======+======+=================+
  """
  waferErrors = \
        _label("ERRORS") + \
        _label("+-------+--------------+------+------+-----------------+") + \
        _label("|       |  Alignment   |Focus | Dyn  |                 |") + \
        _label("|       +------+-------+------+------+                 |") + \
        _label("| Wafer | Pre  |Global |#Errs |#Errs |     Others      |") + \
        _label("+=======+======+=======+======+======+=================+") + \
        pyparsing.OneOrMore( _tableRow( ( waferId, pyparsing.empty, pyparsing.empty, integer, integer, pyparsing.empty ), asList=True ) ) + \
        ( _label("+-------+------+-------+------+------+-----------------+") | 
          _label("+-------+--------------+------+------+-----------------+") )

  """
  ERRORS
  
  +-------+--------------+------+-----------------+
  |       |  Alignment   |Focus |                 |
  |       +------+-------+------+                 |
  | Wafer | Pre  |Global |#Errs |     Others      |
  +=======+======+=======+======+=================+
  |     1 |      |       |    0 |                 |
  +-------+------+-------+------+-----------------+
  """
  waferErrorsAlt = \
        _label("ERRORS") + \
        _label("+-------+--------------+------+-----------------+") + \
        _label("|       |  Alignment   |Focus |                 |") + \
        _label("|       +------+-------+------+                 |") + \
        _label("| Wafer | Pre  |Global |#Errs |     Others      |") + \
        _label("+=======+======+=======+======+=================+") + \
        pyparsing.OneOrMore( _tableRow( ( waferId, pyparsing.empty, pyparsing.empty, integer, pyparsing.empty ), asList=True ) ) + \
        _label("+-------+------+-------+------+-----------------+")

  """
  RETICLE DATA
  
  +--------------------------------------------------------------------------+
  |                           Reticle Corrections                            |
  +--------------+-----------------+---------+---------+------------+--------+
  |              |   Translation   |         |         |            | Energy |
  |              +--------+--------+         |         |            +--------+
  |  Reticle ID  |   X    |   Y    |Rotation |   Mag   |Transmission| Offset |
  |              |  [um]  |  [um]  | [urad]  |  [ppm]  |    [%]     |[mJ/cm2]|
  +==============+========+========+=========+=========+============+========+
  | 5107D1457N1  |  0.000 |  0.000 |    0.00 |    0.00 |      0.0   |    0.0 |
  +--------------+--------+--------+---------+---------+------------+--------+
  """
  reticleData = \
        _label("RETICLE DATA") + \
        _label("+--------------------------------------------------------------------------+") + \
        _label("|                           Reticle Corrections                            |") + \
        _label("+--------------+-----------------+---------+---------+------------+--------+") + \
        _label("|              |   Translation   |         |         |            | Energy |") + \
        _label("|              +--------+--------+         |         |            +--------+") + \
        _label("|  Reticle ID  |   X    |   Y    |Rotation |   Mag   |Transmission| Offset |") + \
        _label("|              |  [um]  |  [um]  | [urad]  |  [ppm]  |    [%]     |[mJ/cm2]|") + \
        _label("+==============+========+========+=========+=========+============+========+") + \
        _tableRow( ( word, fnumber, fnumber, fnumber, fnumber, fnumber, fnumber), asList=True ) + \
        _label("+--------------+--------+--------+---------+---------+------------+--------+")

  """
  ALIGNMENT RESULTS I
  
  +-------+---------------------+---------------------+---------+---------+------+
  |       |    W-translation    |     W-expansion     |         |         |Marks |
  |       +----------+----------+----------+----------+         |         +------+
  | Wafer |    X     |    Y     |    X     |    Y     |  W-rot  | W-orth  |Failed|
  |       |   [um]   |   [um]   |  [ppm]   |  [ppm]   | [urad]  | [urad]  |      |
  +=======+==========+==========+==========+==========+=========+=========+======+
  |     1 |    0.514 |    2.686 |   -0.267 |   -0.267 |   51.89 |   -0.00 |    0 |
  +-------+----------+----------+----------+----------+---------+---------+------+
  """
  alignmentResultsI = \
        _label("ALIGNMENT RESULTS I") + \
        _label("+-------+---------------------+---------------------+---------+---------+------+") + \
        _label("|       |    W-translation    |     W-expansion     |         |         |Marks |") + \
        _label("|       +----------+----------+----------+----------+         |         +------+") + \
        _label("| Wafer |    X     |    Y     |    X     |    Y     |  W-rot  | W-orth  |Failed|") + \
        _label("|       |   [um]   |   [um]   |  [ppm]   |  [ppm]   | [urad]  | [urad]  |      |") + \
        _label("+=======+==========+==========+==========+==========+=========+=========+======+") + \
        pyparsing.OneOrMore( _tableRow( ( waferId, fnumber, fnumber, fnumber, fnumber, fnumber, fnumber, integer ), asList=True ) ) + \
        _label("+-------+----------+----------+----------+----------+---------+---------+------+")

  """
  ALIGNMENT STATISTICS I
  
  +-------+---------------------+---------------------+---------+---------+
  |       |    W-translation    |     W-expansion     |         |         |
  |       +----------+----------+----------+----------+         |         |
  |       |    X     |    Y     |    X     |    Y     |  W-rot  | W-orth  |
  |       |   [um]   |   [um]   |  [ppm]   |  [ppm]   | [urad]  | [urad]  |
  +=======+==========+==========+==========+==========+=========+=========+
  | MIN.  |    0.514 |    2.686 |   -0.267 |   -0.267 |   51.89 |   -0.00 |
  | MAX.  |    0.514 |    2.686 |   -0.267 |   -0.267 |   51.89 |   -0.00 |
  | AVE.  |    0.514 |    2.686 |   -0.267 |   -0.267 |   51.89 |    0.00 |
  | S.D.  |    0.000 |    0.000 |    0.000 |    0.000 |    0.00 |    0.00 |
  +-------+----------+----------+----------+----------+---------+---------+
  """
  alignmentStatsI = \
        _label("ALIGNMENT STATISTICS I") + \
        _label("+-------+---------------------+---------------------+---------+---------+") + \
        _label("|       |    W-translation    |     W-expansion     |         |         |") + \
        _label("|       +----------+----------+----------+----------+         |         |") + \
        _label("|       |    X     |    Y     |    X     |    Y     |  W-rot  | W-orth  |") + \
        _label("|       |   [um]   |   [um]   |  [ppm]   |  [ppm]   | [urad]  | [urad]  |") + \
        _label("+=======+==========+==========+==========+==========+=========+=========+") + \
        pyparsing.OneOrMore( _tableRow( ( tagword, fnumber, fnumber, fnumber, fnumber, fnumber, fnumber ), asList=True ) ) + \
        _label("+-------+----------+----------+----------+----------+---------+---------+")

  """
  ALIGNMENT RESULTS II
  
  +-------+---------+---------+-------------+-----------------------------------+
  |       |         |         |Worst W-qual.|         8.0 to 8.8  [um]          |
  |       |         |         +------+------+--------+--------+--------+--------+
  | Wafer | R-magn  |  R-rot  |M1[%] |M2[%] |  X-M1  |  Y-M1  |  X-M2  |  Y-M2  |
  |       |  [ppm]  | [urad]  |      |      |        |        |        |        |
  +=======+=========+=========+======+======+========+========+========+========+
  |     1 |    0.00 |   17.41 |  68  |      |  0.023 |  0.008 |        |        |
  +-------+---------+---------+------+------+--------+--------+--------+--------+
  """
  alignmentResultsII = \
        _label("ALIGNMENT RESULTS II") + \
        _label("+-------+---------+---------+-------------+-----------------------------------+") + \
        _label("|       |         |         |Worst W-qual.|         8.0 to 8.8  [um]          |") + \
        _label("|       |         |         +------+------+--------+--------+--------+--------+") + \
        _label("| Wafer | R-magn  |  R-rot  |M1[%] |M2[%] |  X-M1  |  Y-M1  |  X-M2  |  Y-M2  |") + \
        _label("|       |  [ppm]  | [urad]  |      |      |        |        |        |        |") + \
        _label("+=======+=========+=========+======+======+========+========+========+========+") + \
        pyparsing.OneOrMore( _tableRow( ( waferId, fnumber, fnumber, integer, (integer|pyparsing.empty), fnumber, fnumber, (fnumber|pyparsing.empty), (fnumber|pyparsing.empty) ), asList=True ) ) + \
        _label("+-------+---------+---------+------+------+--------+--------+--------+--------+")

  """
  ALIGNMENT STATISTICS II
  
  +------+---------+---------+-------------+-----------------------------------+
  |      |         |         |Worst W-qual.|         8.0 to 8.8  [um]          |
  |      |         |         +------+------+--------+--------+--------+--------+
  |      | R-magn  |  R-rot  |M1[%] |M2[%] |  X-M1  |  Y-M1  |  X-M2  |  Y-M2  |
  |      |  [ppm]  | [urad]  |      |      |        |        |        |        |
  +======+=========+=========+======+======+========+========+========+========+
  | MIN. |    0.00 |   17.41 |  68  |      |  0.023 |  0.008 |        |        |
  | MAX. |    0.00 |   17.41 |  68  |      |  0.023 |  0.008 |        |        |
  | AVE. |    0.00 |   17.41 |  68  |   0  |  0.023 |  0.008 |  0.000 |  0.000 |
  | S.D. |    0.00 |    0.00 |   0  |   0  |  0.000 |  0.000 |  0.000 |  0.000 |
  +------+---------+---------+------+------+--------+--------+--------+--------+
  """
  alignmentStatsII = \
        _label("ALIGNMENT STATISTICS II") + \
        _label("+------+---------+---------+-------------+-----------------------------------+") + \
        _label("|      |         |         |Worst W-qual.|         8.0 to 8.8  [um]          |") + \
        _label("|      |         |         +------+------+--------+--------+--------+--------+") + \
        _label("|      | R-magn  |  R-rot  |M1[%] |M2[%] |  X-M1  |  Y-M1  |  X-M2  |  Y-M2  |") + \
        _label("|      |  [ppm]  | [urad]  |      |      |        |        |        |        |") + \
        _label("+======+=========+=========+======+======+========+========+========+========+") + \
        pyparsing.OneOrMore( _tableRow( ( word, fnumber, fnumber, (integer | pyparsing.empty), (integer | pyparsing.empty), fnumber, fnumber, (fnumber | pyparsing.empty), (fnumber | pyparsing.empty) ), asList=True ) ) + \
        _label("+------+---------+---------+------+------+--------+--------+--------+--------+")

  """
  LEVEL RESULTS I
  
  +-------+--------------------------+
  |       |     Global Leveling      |
  |       +--------+--------+--------+
  | Wafer |   Dz   | phi-X  | phi-Y  |
  |       |  [um]  | [urad] | [urad] |
  +=======+========+========+========+
  |     1 |   70.4 |   69.4 |   12.9 |
  +-------+--------+--------+--------+
  """
  levelResultsI = \
        _label("LEVEL RESULTS I") + \
        _label("+-------+--------------------------+") + \
        _label("|       |     Global Leveling      |") + \
        _label("|       +--------+--------+--------+") + \
        _label("| Wafer |   Dz   | phi-X  | phi-Y  |") + \
        _label("|       |  [um]  | [urad] | [urad] |") + \
        _label("+=======+========+========+========+") + \
        pyparsing.OneOrMore( _tableRow( ( waferId, fnumber, fnumber, fnumber ), asList=True ) ) + \
        _label("+-------+--------+--------+--------+")

  """
  LEVEL STATISTICS I
  
  +------+--------------------------+
  |      |     Global Leveling      |
  |      +--------+--------+--------+
  |      |   Dz   | phi-X  | phi-Y  |
  |      |  [um]  | [urad] | [urad] |
  +======+========+========+========+
  | MIN. |   70.4 |   69.4 |   12.9 |
  | MAX. |   70.4 |   69.4 |   12.9 |
  | AVE. |   70.4 |   69.4 |   12.9 |
  | S.D. |    0.0 |    0.0 |    0.0 |
  +------+--------+--------+--------+
  """
  levelStatsI = \
        _label("LEVEL STATISTICS I") + \
        _label("+------+--------------------------+") + \
        _label("|      |     Global Leveling      |") + \
        _label("|      +--------+--------+--------+") + \
        _label("|      |   Dz   | phi-X  | phi-Y  |") + \
        _label("|      |  [um]  | [urad] | [urad] |") + \
        _label("+======+========+========+========+") + \
        pyparsing.OneOrMore( _tableRow( ( word, fnumber, fnumber, fnumber ), asList=True ) ) + \
        _label("+------+--------+--------+--------+")

  """
  LEVEL RESULTS II
  
  +-------+-----------------------------------------------------+
  |       |                Field*Field Leveling                 |
  |       +--------------------------+--------------------------+
  |       |      minimum value       |      maximum value       |
  |       +--------+--------+--------+--------+--------+--------+
  | Wafer |   Dz   | phi-X  | phi-Y  |   Dz   | phi-X  | phi-Y  |
  |       |  [um]  | [urad] | [urad] |  [um]  | [urad] | [urad] |
  +=======+========+========+========+========+========+========+
  |     1 |   68.9 |    2.9 |  -26.4 |   74.3 |   52.5 |    9.2 |
  +-------+--------+--------+--------+--------+--------+--------+
  """
  levelResultsII = \
        _label("LEVEL RESULTS II") + \
        _label("+-------+-----------------------------------------------------+") + \
        _label("|       |                Field*Field Leveling                 |") + \
        _label("|       +--------------------------+--------------------------+") + \
        _label("|       |      minimum value       |      maximum value       |") + \
        _label("|       +--------+--------+--------+--------+--------+--------+") + \
        _label("| Wafer |   Dz   | phi-X  | phi-Y  |   Dz   | phi-X  | phi-Y  |") + \
        _label("|       |  [um]  | [urad] | [urad] |  [um]  | [urad] | [urad] |") + \
        _label("+=======+========+========+========+========+========+========+") + \
        pyparsing.OneOrMore( _tableRow( ( waferId, fnumber, fnumber, fnumber, fnumber, fnumber, fnumber ), asList=True ) ) + \
        _label("+-------+--------+--------+--------+--------+--------+--------+")

  """
  LEVEL STATISTICS II
  
  +------+-----------------------------------------------------+
  |      |                Field*Field Leveling                 |
  |      +--------------------------+--------------------------+
  |      |      minimum value       |      maximum value       |
  |      +--------+--------+--------+--------+--------+--------+
  |      |   Dz   | phi-X  | phi-Y  |   Dz   | phi-X  | phi-Y  |
  |      |  [um]  | [urad] | [urad] |  [um]  | [urad] | [urad] |
  +======+========+========+========+========+========+========+
  | MIN. |   68.9 |    2.9 |  -26.4 |   74.3 |   52.5 |    9.2 |
  | MAX. |   68.9 |    2.9 |  -26.4 |   74.3 |   52.5 |    9.2 |
  | AVE. |   68.9 |    2.9 |  -26.4 |   74.3 |   52.5 |    9.2 |
  | S.D. |    0.0 |    0.0 |    0.0 |    0.0 |    0.0 |    0.0 |
  +------+--------+--------+--------+--------+--------+--------+
  """
  levelStatsII = \
        _label("LEVEL STATISTICS II") + \
        _label("+------+-----------------------------------------------------+") + \
        _label("|      |                Field*Field Leveling                 |") + \
        _label("|      +--------------------------+--------------------------+") + \
        _label("|      |      minimum value       |      maximum value       |") + \
        _label("|      +--------+--------+--------+--------+--------+--------+") + \
        _label("|      |   Dz   | phi-X  | phi-Y  |   Dz   | phi-X  | phi-Y  |") + \
        _label("|      |  [um]  | [urad] | [urad] |  [um]  | [urad] | [urad] |") + \
        _label("+======+========+========+========+========+========+========+") + \
        pyparsing.OneOrMore( _tableRow( ( word, fnumber, fnumber, fnumber, fnumber, fnumber, fnumber ), asList=True ) ) + \
        _label("+------+--------+--------+--------+--------+--------+--------+")

  """
  LEVEL RESULTS III
  
  +-------+-----------------------------------------------------+
  |       |                Field*Field Leveling                 |
  |       +--------------------------+--------------------------+
  |       |        mean value        |    standard deviation    |
  |       +--------+--------+--------+--------+--------+--------+
  | Wafer |   Dz   | phi-X  | phi-Y  |   Dz   | phi-X  | phi-Y  |
  |       |  [um]  | [urad] | [urad] |  [um]  | [urad] | [urad] |
  +=======+========+========+========+========+========+========+
  |     1 |   71.7 |   31.9 |   -9.0 |    1.5 |   10.6 |    8.8 |
  +-------+--------+--------+--------+--------+--------+--------+
  """
  levelResultsIII = \
        _label("LEVEL RESULTS III") + \
        _label("+-------+-----------------------------------------------------+") + \
        _label("|       |                Field*Field Leveling                 |") + \
        _label("|       +--------------------------+--------------------------+") + \
        _label("|       |        mean value        |    standard deviation    |") + \
        _label("|       +--------+--------+--------+--------+--------+--------+") + \
        _label("| Wafer |   Dz   | phi-X  | phi-Y  |   Dz   | phi-X  | phi-Y  |") + \
        _label("|       |  [um]  | [urad] | [urad] |  [um]  | [urad] | [urad] |") + \
        _label("+=======+========+========+========+========+========+========+") + \
        pyparsing.OneOrMore( _tableRow( ( waferId, fnumber, fnumber, fnumber, fnumber, fnumber, fnumber ), asList=True ) ) + \
        _label("+-------+--------+--------+--------+--------+--------+--------+")

  """
  LEVEL STATISTICS III
  
  +------+-----------------------------------------------------+
  |      |                Field*Field Leveling                 |
  |      +--------------------------+--------------------------+
  |      |        mean value        |    standard deviation    |
  |      +--------+--------+--------+--------+--------+--------+
  |      |   Dz   | phi-X  | phi-Y  |   Dz   | phi-X  | phi-Y  |
  |      |  [um]  | [urad] | [urad] |  [um]  | [urad] | [urad] |
  +======+========+========+========+========+========+========+
  | MIN. |   71.7 |   31.9 |   -9.0 |    1.5 |   10.6 |    8.8 |
  | MAX. |   71.7 |   31.9 |   -9.0 |    1.5 |   10.6 |    8.8 |
  | AVE. |   71.7 |   31.9 |   -9.0 |    1.5 |   10.6 |    8.8 |
  | S.D. |    0.0 |    0.0 |    0.0 |    0.0 |    0.0 |    0.0 |
  +------+--------+--------+--------+--------+--------+--------+
  """
  levelStatsIII = \
        _label("LEVEL STATISTICS III") + \
        _label("+------+-----------------------------------------------------+") + \
        _label("|      |                Field*Field Leveling                 |") + \
        _label("|      +--------------------------+--------------------------+") + \
        _label("|      |        mean value        |    standard deviation    |") + \
        _label("|      +--------+--------+--------+--------+--------+--------+") + \
        _label("|      |   Dz   | phi-X  | phi-Y  |   Dz   | phi-X  | phi-Y  |") + \
        _label("|      |  [um]  | [urad] | [urad] |  [um]  | [urad] | [urad] |") + \
        _label("+======+========+========+========+========+========+========+") + \
        pyparsing.OneOrMore( _tableRow( ( word, fnumber, fnumber, fnumber, fnumber, fnumber, fnumber ), asList=True ) ) + \
        _label("+------+--------+--------+--------+--------+--------+--------+")

  """
  ALIGNMENT RESULTS III
  
  +-------+-------------------------+---------------+-------------+-----------+
  |       |      level sensor       | lens element  |             |           |
  |       +-------+--------+--------+-------+-------+             |           |
  | Wafer |   Z   |   Rx   |   Ry   |  #1   |  #2   |reticle table|wavelength |
  |       | [um]  | [urad] | [urad] | [um]  | [um]  |    [um]     |   [pm]    |
  +=======+=======+========+========+=======+=======+=============+===========+
  |     1 |   2.0 |  -88.7 |   25.8 |   0.5 |  12.1 |      8.2    |   -41.3   |
  +-------+-------+--------+--------+-------+-------+-------------+-----------+
  """
  alignmentResultsIII = \
        _label("ALIGNMENT RESULTS III") + \
        _label("+-------+-------------------------+---------------+-------------+-----------+") + \
        _label("|       |      level sensor       | lens element  |             |           |") + \
        _label("|       +-------+--------+--------+-------+-------+             |           |") + \
        _label("| Wafer |   Z   |   Rx   |   Ry   |  #1   |  #2   |reticle table|wavelength |") + \
        _label("|       | [um]  | [urad] | [urad] | [um]  | [um]  |    [um]     |   [pm]    |") + \
        _label("+=======+=======+========+========+=======+=======+=============+===========+") + \
        pyparsing.OneOrMore( _tableRow( ( waferId, fnumber, fnumber, fnumber, fnumber, fnumber, fnumber, fnumber ), asList=True ) ) + \
        _label("+-------+-------+--------+--------+-------+-------+-------------+-----------+")


  """
  ALIGNMENT RESULTS IV
  
  +-------+-----------------------+-----------------------+
  |       |         Scan          |  R-Stage Translation  |
  |       +-----------+-----------+-----------+-----------+
  | Wafer |  Scaling  |   Skew    |     X     |     Y     |
  |       |   [ppm]   |  [urad]   |   [um]    |   [um]    |
  +=======+===========+===========+===========+===========+
  |     1 |      0.06 |     -7.28 |    -8.443 |     8.587 |
  +-------+-----------+-----------+-----------+-----------+
  """
  alignmentResultsIV = \
        _label("ALIGNMENT RESULTS IV") + \
        _label("+-------+-----------------------+-----------------------+") + \
        _label("|       |         Scan          |  R-Stage Translation  |") + \
        _label("|       +-----------+-----------+-----------+-----------+") + \
        _label("| Wafer |  Scaling  |   Skew    |     X     |     Y     |") + \
        _label("|       |   [ppm]   |  [urad]   |   [um]    |   [um]    |") + \
        _label("+=======+===========+===========+===========+===========+") + \
        pyparsing.OneOrMore( _tableRow( ( waferId, fnumber, fnumber, fnumber, fnumber ), asList=True ) ) + \
        _label("+-------+-----------+-----------+-----------+-----------+")

  """
  ALIGNMENT STATISTICS IV
  
  +------+-----------------------+-----------------------+
  |      |         Scan          |  R-Stage Translation  |
  |      +-----------+-----------+-----------+-----------+
  |      |  Scaling  |   Skew    |     X     |     Y     |
  |      |   [ppm]   |  [urad]   |   [um]    |   [um]    |
  +======+===========+===========+===========+===========+
  | MIN. |      0.06 |     -7.28 |    -8.443 |     8.587 |
  | MAX. |      0.06 |     -7.28 |    -8.443 |     8.587 |
  | AVE. |      0.06 |     -7.28 |    -8.443 |     8.587 |
  | S.D. |      0.00 |      0.00 |     0.000 |     0.000 |
  +------+-----------+-----------+-----------+-----------+
  """
  alignmentStatsIV = \
        _label("ALIGNMENT STATISTICS IV") + \
        _label("+------+-----------------------+-----------------------+") + \
        _label("|      |         Scan          |  R-Stage Translation  |") + \
        _label("|      +-----------+-----------+-----------+-----------+") + \
        _label("|      |  Scaling  |   Skew    |     X     |     Y     |") + \
        _label("|      |   [ppm]   |  [urad]   |   [um]    |   [um]    |") + \
        _label("+======+===========+===========+===========+===========+") + \
        pyparsing.OneOrMore( _tableRow( ( word, fnumber, fnumber, fnumber, fnumber ), asList=True ) ) + \
        _label("+------+-----------+-----------+-----------+-----------+")

  """
  DYNAMIC PERFORMANCE STATISTICS
  
  +------+-----------------------------------+-----------------------------------+
  |      |       Moving Average Error        |        Moving Stdev Error         |
  |      +--------+--------+--------+--------+--------+--------+--------+--------+
  |      |   X    |   Y    |   Rz   |   Z    |   X    |   Y    |   Rz   |   Z    |
  |      |  [nm]  |  [nm]  | [urad] |  [nm]  |  [nm]  |  [nm]  | [urad] |  [nm]  |
  +======+========+========+========+========+========+========+========+========+
  | MIN. |    0.6 |    0.8 |    0.0 |    0.0 |    4.6 |    4.6 |    0.1 |    0.0 |
  | MAX. |    1.4 |    1.4 |    0.1 |   24.2 |   11.2 |   11.2 |    0.3 |   58.8 |
  | AVE. |    0.9 |    1.1 |    0.1 |   14.0 |    6.4 |    6.6 |    0.1 |   36.9 |
  | S.D. |    0.2 |    0.1 |    0.0 |    6.1 |    1.1 |    1.5 |    0.0 |   12.9 |
  +------+--------+--------+--------+--------+--------+--------+--------+--------+
  """
  dynamicPerformanceStats = \
        _label("DYNAMIC PERFORMANCE STATISTICS") + \
        _label("+------+-----------------------------------+-----------------------------------+") + \
        _label("|      |       Moving Average Error        |        Moving Stdev Error         |") + \
        _label("|      +--------+--------+--------+--------+--------+--------+--------+--------+") + \
        _label("|      |   X    |   Y    |   Rz   |   Z    |   X    |   Y    |   Rz   |   Z    |") + \
        _label("|      |  [nm]  |  [nm]  | [urad] |  [nm]  |  [nm]  |  [nm]  | [urad] |  [nm]  |") + \
        _label("+======+========+========+========+========+========+========+========+========+") + \
        pyparsing.OneOrMore( _tableRow( ( word, fnumber, fnumber, fnumber, fnumber, fnumber, fnumber, fnumber, fnumber ), asList=True ) ) + \
        _label("+------+--------+--------+--------+--------+--------+--------+--------+--------+")

  """
  LEVEL RESULTS IV
  
  +-------+-------------------------------------------------------+
  |       |                Intra Field Tilt Range                 |
  |       +---------------------------+---------------------------+
  |       |            Rx             |            Ry             |
  |       +------+------+------+------+------+------+------+------+
  | Wafer | Min  | Max  | Ave  | Sdv  | Min  | Max  | Ave  | Sdv  |
  |       |[urad]|[urad]|[urad]|[urad]|[urad]|[urad]|[urad]|[urad]|
  +=======+======+======+======+======+======+======+======+======+
  |     1 |   9  |  58  |  24  |   9  |   7  |  49  |  18  |   9  |
  +-------+------+------+------+------+------+------+------+------+
  """
  levelResultsIV = \
        _label("LEVEL RESULTS IV") + \
        _label("+-------+-------------------------------------------------------+") + \
        _label("|       |                Intra Field Tilt Range                 |") + \
        _label("|       +---------------------------+---------------------------+") + \
        _label("|       |            Rx             |            Ry             |") + \
        _label("|       +------+------+------+------+------+------+------+------+") + \
        _label("| Wafer | Min  | Max  | Ave  | Sdv  | Min  | Max  | Ave  | Sdv  |") + \
        _label("|       |[urad]|[urad]|[urad]|[urad]|[urad]|[urad]|[urad]|[urad]|") + \
        _label("+=======+======+======+======+======+======+======+======+======+") + \
        pyparsing.OneOrMore( _tableRow( ( waferId, integer, integer, integer, integer, integer, integer, integer, integer ), asList=True ) ) + \
        _label("+-------+------+------+------+------+------+------+------+------+")

  """
  LEVEL STATISTICS IV
  
  +-------+-------------------------------------------------------+
  |       |                Intra Field Tilt Range                 |
  |       +---------------------------+---------------------------+
  |       |            Rx             |            Ry             |
  |       +------+------+------+------+------+------+------+------+
  |       | Min  | Max  | Ave  | Sdv  | Min  | Max  | Ave  | Sdv  |
  |       |[urad]|[urad]|[urad]|[urad]|[urad]|[urad]|[urad]|[urad]|
  +=======+======+======+======+======+======+======+======+======+
  | MIN.  |   9  |  58  |  24  |   9  |   7  |  49  |  18  |   9  |
  | MAX.  |   9  |  58  |  24  |   9  |   7  |  49  |  18  |   9  |
  | AVE.  |   9  |  58  |  24  |   9  |   7  |  49  |  18  |   9  |
  | S.D.  |   0  |   0  |   0  |   0  |   0  |   0  |   0  |   0  |
  +-------+------+------+------+------+------+------+------+------+
  """
  levelStatsIV = \
        _label("LEVEL STATISTICS IV") + \
        _label("+-------+-------------------------------------------------------+") + \
        _label("|       |                Intra Field Tilt Range                 |") + \
        _label("|       +---------------------------+---------------------------+") + \
        _label("|       |            Rx             |            Ry             |") + \
        _label("|       +------+------+------+------+------+------+------+------+") + \
        _label("|       | Min  | Max  | Ave  | Sdv  | Min  | Max  | Ave  | Sdv  |") + \
        _label("|       |[urad]|[urad]|[urad]|[urad]|[urad]|[urad]|[urad]|[urad]|") + \
        _label("+=======+======+======+======+======+======+======+======+======+") + \
        pyparsing.OneOrMore( _tableRow( ( tagword, integer, integer, integer, integer, integer, integer, integer, integer ), asList=True ) ) + \
        _label("+-------+------+------+------+------+------+------+------+------+")

#          ( pyparsing.Dict( waferData1 ).setResultsName("waferData") | \
#            pyparsing.Dict( waferData2 ).setResultsName("waferData") )+ \
#        pyparsing.Group( batchData ).setResultsName("batchData") + 
  return ( pyparsing.Group( hdr ).setResultsName("header") + 
        pyparsing.Group( batchDataHdr ).setResultsName("batchDataHeader") + 
        pyparsing.Group( processData1 | processData2 ).setResultsName("processData") + 
        pyparsing.Optional( pyparsing.Group( exposureData ).setResultsName("exposureData") ) + 
        pyparsing.Group( processDataContd ).setResultsName("processData2") + 
        explanationLabel + 
        pyparsing.Group( batchData ).setResultsName("batchData") + 
        pyparsing.Group( processCorrections ).setResultsName("processCorrections") + 
        pyparsing.Group( batchMonitoringData ).setResultsName("batchMonitoringData") + 
        pyparsing.Optional( pyparsing.Group( imageData ).setResultsName("imageData") ) + 
        pyparsing.Dict( waferData1 | waferData2 ).setResultsName("waferData") + 
        pyparsing.Group( waferErrors ).setResultsName("waferErrors") + 
        pyparsing.Group( reticleData ).setResultsName("reticleData") + 
        pyparsing.Group( alignmentResultsI ).setResultsName("alignmentResultsI") + 
        pyparsing.Group( alignmentStatsI ).setResultsName("alignmentStatsI") + 
        pyparsing.Group( alignmentResultsII ).setResultsName("alignmentResultsII") + 
        pyparsing.Group( alignmentStatsII ).setResultsName("alignmentStatsII") + 
        pyparsing.Group( levelResultsI ).setResultsName("levelResultsI") + 
        pyparsing.Group( levelStatsI ).setResultsName("levelStatsI") + 
        pyparsing.Group( levelResultsII ).setResultsName("levelResultsII") + 
        pyparsing.Group( levelStatsII ).setResultsName("levelStatsII") + 
        pyparsing.Group( levelResultsIII ).setResultsName("levelResultsIII") + 
        pyparsing.Group( levelStatsIII ).setResultsName("levelStatsIII") + 
        pyparsing.Group( alignmentResultsIII ).setResultsName("alignmentResultsIII") + 
        pyparsing.Group( alignmentResultsIV ).setResultsName("alignmentResultsIV") + 
        pyparsing.Group( alignmentStatsIV ).setResultsName("alignmentStatsIV") + 
        pyparsing.Group( dynamicPerformanceStats ).setResultsName("dynamicPerformanceStats") + 
        pyparsing.Group( levelResultsIV ).setResultsName("levelResultsIV") + 
        pyparsing.Dict( levelStatsIV ).setResultsName("levelStatsIV")
        ).setResultsName("ASML")


if __name__ == "__main__":
  import lwXMLparser as xmlP
  
  #~ infile = file("24141506_P5107RM59_399A1457N1_PHS04")                            # wafer
  #~ infile = file("24141506_P5107RM59_399A1457N1_PHS04B")                          # 1 wafer, retest
  infile = file("24157800_P5107RM74_399A1828M1_PHS04")   # 13 wafers
  #~ infile = file("A52759.txt") # 25 wafers, alternate format
  filelines = infile.readlines()
  infile.close()

  # merge incoming lines into one long string for pyparsing
  filetext = "".join( filelines )
  
  results = BNF().parseString( filetext )
  
  results = BNF().parseFile("A52759.txt")

  pp = pprint.PrettyPrinter(2)

  # print results,  breaking up lists onto separate lines for readability
  #print "]\n [".join( str( results ).split("], [") )
  #~ pp.pprint( results.asList() )
  print results.asXML(None)
  #~ print results.asXML(None, True)
  print results.batchData.asXML()
  print results.batchData.asXML(None,True)
  print
  print results.batchData.asXML(None,formatted=False)
  
  #~ doc = xmlP.XMLDocument()
  #~ doc.parseString( resx )
  #~ print doc

  if len(results) > 0:
    print "results.header =",
    print results.header
    print ",\n ".join( str( results.header ).split(", ") )
    print
    
    # now print just the batchData section of the results
    print "results.batchData ="
    print results.batchData
    print ",\n ".join( str( results.batchData ).split(", ") )
    #~ pp.pprint( results.batchData.asList() )
    
    # print some sub-fields within this section
    print "results.batchData.trackInputUsed =",results.batchData.trackInputUsed
    print "results.batchData.trackOutputUsed =",results.batchData.trackOutputUsed
    print "results.batchData.maxDelta =",results.batchData.maxDelta
    
    # print fields from within a table
    print results.waferData
    for wd in ( results.waferData ):
      print "Wafer",wd.wafernum, "- begin:", wd.procBegin, "- end:", wd.procEnd
  
    # print each line from within a table
    print results.waferData
    for i in range( len( results.waferData ) ):
      print "Wafer", results.waferData[i].wafernum, "- begin:", \
                     results.waferData[i].procBegin, "- end:", \
                     results.waferData[i].procEnd
  
    # access the same table by keys, not by iterating over list
    #~ print results.waferData
    #~ wdKeys = results.waferData.keys()
    #~ intStrCompare = lambda a,b: int(a)-int(b)
    #~ wdKeys.sort( intStrCompare )
    #~ wd = results.waferData
    #~ for k in wdKeys:
      #~ print "Wafer",k, "- begin:", wd[k].procBegin, "- end:", wd[k].procEnd
  
    # access entries in a dictionary
    print "results.levelStatsIV ="
    #~ print "]\n [".join( str( results.levelStatsIV ).split("], [") )
    pp.pprint( results.levelStatsIV.asList() )
    print "results.levelStatsIV.keys() =",results.levelStatsIV.keys()
    print "results.levelStatsIV['MAX'] =", results.levelStatsIV['MAX']
    print "results.levelStatsIV.MAX    =", results.levelStatsIV.MAX

  else:
    print "failed to match BNF"
