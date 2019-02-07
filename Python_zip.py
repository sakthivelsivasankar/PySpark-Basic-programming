"""
# Python code to demonstrate the working of  zip() 

"""
# initializing lists 
name = [ "Sunil", "Anil", "Ramesh", "Suresh" ] 
roll_no = [ 4, 1, 3, 2 ] 
marks = [ 40, 50, 60, 70 ] 
  
# using zip() to map values 
mapped = zip(name, roll_no, marks) 
  
# converting values to print as set 
mapped = set(mapped) 
  
# printing resultant values  
print ("The zipped result is : ") 
print (mapped) 

########################################################
# Python code to demonstrate the working of  
# unzip 
  
# unzipping values 
namz, roll_noz, marksz = zip(*mapped) 
  
print ("The unzipped result: \n") 
  
# printing initial lists 
print ("The name list is : ")
print (namz) 
  
print ("The roll_no list is : ")
print (roll_noz) 
  
print ("The marks list is : ")
print (marksz)

########################################################

players = [ "Ram", "Ajith", "Sunil", "Shah", "Krishna" ] 
  
# initializing their scores 
scores = [100, 15, 17, 28, 43 ] 
  
# printing players and scores. 
for pl, sc in zip(players, scores): 
    print ("Player :  %s     Score : %d" %(pl, sc)) 
    
#######################################################
