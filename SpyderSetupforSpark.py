"""
Make sure you give execute privileges
-----------------------------------------------------------------------------
Spark with Python: Setup Spyder IDE for Spark
Execute this script once when Spyder is started on Windows
-----------------------------------------------------------------------------
"""

import os
import sys
os.chdir("C:\spark\spark-2.3.2-bin-hadoop2.7\python")
os.curdir

# Configure SPARK Home. Set this up to the directory where Spark is installed
if 'SPARK_HOME' not in os.environ:
    os.environ['SPARK_HOME'] = 'C:\spark\spark-2.3.2-bin-hadoop2.7'
    
# Create a variable for our root path
SPARK_HOME = os.environ['SPARK_HOME']

#Add the following paths to the system path. Please check your installation #to make sure that these zip files actually exist. 
sys.path.insert(0,os.path.join(SPARK_HOME,"python"))
sys.path.insert(0,os.path.join(SPARK_HOME,"python","lib"))
sys.path.insert(0,os.path.join(SPARK_HOME,"python","lib","pyspark.zip"))
sys.path.insert(0,os.path.join(SPARK_HOME,"python","lib","py4j-0.10.7-src.zip"))

#Initiate Spark context. Once this is done all other applications can run
from pyspark import SparkContext
from pyspark import SparkConf

# Optionally configure Spark Settings
conf=SparkConf()
conf.set("spark.executor.memory", "1g")
conf.set("spark.cores.max", "2")
conf.setAppName("appname")

## Initialize SparkContext. Run only once. Otherwise you get multiple Context Error.
sc = SparkContext('local', conf=conf)

#Test to make sure everything works. ~ lines count
lines=sc.textFile("test.csv")
lines.count()

#word count
text_file=sc.textFile("test.txt")
words = text_file.flatMap(lambda line: line.split(" ")) \
             .map(lambda word: (word, 1)) \
             .reduceByKey(lambda a, b: a + b)
words.count()
