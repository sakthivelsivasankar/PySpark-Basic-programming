"""
SpeechRecognition Voice2Text

pip install SpeechRecognition
pip install PyAudio
"""
##########################################
import speech_recognition as sr
r = sr.Recognizer()
with sr.Microphone() as source:
    print("Say something")
    audio=r.listen(source)
    print("time over, thanks")

try:
    print("TEXT: " + r.recognize_google(audio));
except:
    pass;
    
#########################################
#NOTE: this requires PyAudio because it uses the Microphone class

import speech_recognition as sr
r = sr.Recognizer()
with sr.Microphone() as source:                # use the default microphone as the audio source
    audio = r.listen(source)                   # listen for the first phrase and extract it into audio data

try:
    print("You said " + r.recognize(audio))    # recognize speech using Google Speech Recognition
except LookupError:                            # speech is unintelligible
    print("Could not understand audio")
    
##########################################
import speech_recognition as sr

r = sr.Recognizer()
with sr.AudioFile("C:/Users/lenovodolby/Documents/Sound recordings/test.wav") as source:
    audio=r.record(source)

try:
#   s1 = r.recognize_google(audio);
    s2 = r.recognize_google(audio, language='fr-FR')   #for reginal language font to be printed
    print(s2)
except Exception as e:
    print("Exception: "+str(e))
    
##########################################
