import sys
import time
import matchers.Matcher_StaticTracker as matchedImproved
import parsers.XMLreader as xmlreader
import os
import pandas as pd
import jpype
import Utils as utils
import matchers.MatchedPairsCollector as MatchedPairsCollector
import yaml


## set your config file here.
# config_file = r"/home/junjie/Desktop/tracking_static/FixPatternMining_publish/config.yaml"
config_file = sys.argv[1]
with open(config_file, 'r') as stream:
    configs = yaml.safe_load(stream)
print(configs)

##start JVM to load RefactoringMiner

java_jar_path = configs['java_jar_path']
java_dependency_path = configs.get('java_dependency_path', None)
jarpath = os.path.join(os.path.abspath('.'),
                       java_jar_path)
if java_dependency_path:
    dependency = os.path.join(os.path.abspath('.'),
                                java_dependency_path )

jvmPath = jpype.getDefaultJVMPath()

# On macOS, especially OpenJDK 19+ arm64, getDefaultJVMPath() can return
# an incorrect or non-existent path.  If JAVA_HOME is set (or if the default
# path does not exist), resolve the dylib directly from JAVA_HOME.
_java_home = os.environ.get("JAVA_HOME", "")
if _java_home:
    _candidate = os.path.join(_java_home, "lib", "server", "libjvm.dylib")
    if os.path.exists(_candidate):
        jvmPath = _candidate
elif jvmPath and 'libjli.dylib' in jvmPath:
    alt_jvmPath = jvmPath.replace('libjli.dylib', 'server/libjvm.dylib')
    if not os.path.exists(alt_jvmPath):
        alt_jvmPath = jvmPath.replace('MacOS/libjli.dylib', 'Home/lib/server/libjvm.dylib')
    jvmPath = alt_jvmPath if os.path.exists(alt_jvmPath) else jvmPath


import glob
if not jpype.isJVMStarted():
    jpype.addClassPath(jarpath)
    if java_dependency_path:
        for jar in glob.glob(os.path.join(dependency, "*.jar")):
            jpype.addClassPath(jar)
    jpype.startJVM(jvmPath, "-ea")

jClass = jpype.JClass("edu.concordia.junjie.RefactoringInfo")

remote_repo_path = configs['remote_repo_path']
local_repo_path = configs['loc_repo_path']

parentCommit = configs['parent_commit']
childCommit = configs['child_commit']
child_report_path = configs['child_report_path']
parent_report_path = configs['parent_report_path']

saveResultsPath = configs['save_result_path']

staticTool = configs['static_tool']
if staticTool == 'Spotbugs':
    Reader = xmlreader.SpotbugsReader
elif staticTool == 'PMD':
    Reader = xmlreader.PMDReader
elif staticTool == 'DesignitePy':
    from parsers.CSVParser import DesignitePyCSVReader
    Reader = DesignitePyCSVReader
else:
    print(f"Unknow static tool: {staticTool}")
    exit(1)


goneResultsPath = os.path.join(saveResultsPath, 'gone')
newResultsPath = os.path.join(saveResultsPath, 'new')
if not os.path.exists(goneResultsPath):
    os.makedirs(goneResultsPath, exist_ok=True)
if not os.path.exists(newResultsPath):
    os.makedirs(newResultsPath, exist_ok=True)


###step1 read commitlist and set parent commit and child commit
print(f"stat to analyze the repo: {remote_repo_path}")
print(f"static_tool:{staticTool}\nchild commit:{childCommit}")

parentBuginstances = Reader(parent_report_path)
childBuginstances = Reader(child_report_path)

matchingStartTime = time.time()

#### Run StaticTracker
unmatchedChild, unmatchedParent,matchedPairs = matchedImproved.matchChildParent(local_repo_path, parentBuginstances, childBuginstances,
                                                        parentCommit, childCommit, remote_repo_path, jClass)
matchingEndTime = time.time()

utils.writeToGoneNew(unmatchedParent, unmatchedChild,  parentCommit, childCommit, goneResultsPath, newResultsPath)
row = [childCommit, matchingEndTime - matchingStartTime]
# utils.writeToTime(timeMeasurePath, row)
matchedPairsSavePath = os.path.join(saveResultsPath, str(childCommit) + '_matched_pairs' + '.xml')
MatchedPairsCollector.wrtieToXML(matchedPairs, matchedPairsSavePath)
print(f"finish the matching of {staticTool}")


jpype.shutdownJVM()