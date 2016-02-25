import sys
from optparse import OptionParser
import xml.dom.minidom
import re
import glsapiutil
from xml.dom.minidom import parseString

HOSTNAME = 'http://192.168.8.10:8080'
VERSION = "v2"

DEBUG = "false"
api = None

#####################################################################################

HiSeqWF = 'Nextera Rapid Capture for HiSeq 5.0'
HiSeqStage = 'Tagment DNA (Nextera Rapid Capture) 5.0'

MSeqWF = 'Nextera DNA for MiSeq 5.0'
MSeqStage = 'Tagment DNA (Nextera DNA) 5.0'

#####################################################################################


def getStageURI( wfName, stageName ):

	response = ""

	wURI = HOSTNAME + "/api/" + VERSION + "/configuration/workflows"
	wXML = api.getResourceByURI( wURI )
	wDOM = parseString( wXML )

	workflows = wDOM.getElementsByTagName( "workflow" )
	for wf in workflows:
		name = wf.getAttribute( "name" )

		if name == wfName:
			wfURI = wf.getAttribute( "uri" )
			wfXML = api.getResourceByURI( wfURI )
			wfDOM = parseString( wfXML )

			stages = wfDOM.getElementsByTagName( "stage" )
			for stage in stages:
				stagename = stage.getAttribute( "name" )
				if stagename == stageName:
					response = stage.getAttribute( "uri" )
					break

			break
	return response


def routeAnalytes( pLUID, HiSeq, MiSeq):

	ANALYTES = []		### Cache
	GoTo_HiSeq = []
	GoTo_MiSeq = []

	## Step 1: Get the process XML #technically step XML not process
	processURI = HOSTNAME + "/api/" + VERSION + "/steps/" + pLUID + "/details" #
	processXML = api.getResourceByURI( processURI )
	processDOM = parseString( processXML )

	## Step 2: Harvest Output Analytes
	analytes = processDOM.getElementsByTagName( "output" )

	## Step 3: looks for ones
	for analyte in analytes:

		if analyte.getAttribute( "type" ) == "Analyte":

			analyteURI = analyte.getAttribute( "uri" )
			if analyteURI in ANALYTES:
				pass
			else:
				ANALYTES.append( analyteURI )
				analyteXML = api.getResourceByURI( analyteURI )
				analyteDOM = parseString( analyteXML )

		## Step 4: Add the analytes to the list of ones to be routed

				if api.getUDF( analyteDOM , "Go to HiSeq" ) == 'true':
					GoTo_HiSeq.append( analyteURI )
				if api.getUDF( analyteDOM , "Go to MiSeq" ) == 'true':
					GoTo_MiSeq.append( analyteURI )

	def pack_and_go( stageURI, a_ToGo ):

		## Step 5: Build and submit the routing message
		rXML = '<rt:routing xmlns:rt="http://genologics.com/ri/routing">'
		rXML = rXML + '<assign stage-uri="' + stageURI + '">'
		for uri in a_ToGo:
			rXML = rXML + '<artifact uri="' + uri + '"/>'
		rXML = rXML + '</assign>'
		rXML = rXML + '</rt:routing>'

		response = api.createObject( rXML, HOSTNAME + "/api/" + VERSION + "/route/artifacts/" )
#		print response

	Mi_r = pack_and_go( MiSeq, GoTo_MiSeq)
	Hi_r = pack_and_go( HiSeq, GoTo_HiSeq)

	msg = str( len(GoTo_MiSeq) ) + " Samples were added to the " + MSeqStage + " Step. " + str( len(GoTo_HiSeq) ) + " Samples were added to the " + HiSeqStage + " Step."
	print msg
	status = "OK"
	api.reportScriptStatus( options.stepURI, status, msg )

def main():

	global api
	global options

	parser = OptionParser()
	parser.add_option( "-u", "--username", help="username of the current user", action = 'store' ,dest = 'username')
	parser.add_option( "-p", "--password", help="password of the current user")
	parser.add_option( "-l", "--limsid", help="the limsid of the process under investigation")
	parser.add_option( "-s", "--stepURI", help="the URI of the step that launched this script")

	(options, args) = parser.parse_args()

	api = glsapiutil.glsapiutil()
	api.setHostname( HOSTNAME )
	api.setVersion( "v2" )
	api.setup( options.username, options.password )

	MiSeqURI = getStageURI( MSeqWF, MSeqStage )
	HiSeqURI = getStageURI( HiSeqWF, HiSeqStage )

	if MiSeqURI == "" or HiSeqURI == "":
		print "Could not retrieve the workflow / stage combination"
#	else:
#		print MiSeqURI
#		print HiSeqURI

	routeAnalytes( options.limsid, HiSeqURI, MiSeqURI)

if __name__ == "__main__":
	main()
