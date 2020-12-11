import sys,os,glob
import speech_recognition as sr 

filenames = glob.glob('/home/luvitusmaximus/Documents/ASR/SampleAudioFiles/WAVFiles/CHUNKS/' + '*.wav')
for file in filenames:
    r = sr.Recognizer() 

    with sr.AudioFile(file) as source: 
#reads the audio file. Here we use record instead of 
#listen 
        audio = r.record(source) 
    filename = file +'.txt'
    try: 
#print("The audio file contains: " + r.recognize_google(audio)) 
        f=open(filename,"x") #give a text file for output
        f.write("%s \t %s \n" %(file,r.recognize_google(audio, language = 'hi-IN')))
    except sr.UnknownValueError: 
            f.write("%s \t %s \n" %(file,"Google Speech Recognition could not understand audio") )

    except sr.RequestError as e: 
            f.write("%s \t %s \n" %(file,"Could not request results from Google Speech Recognition service; {0}.format(e)") )

#output=google.language.transliterate( r.recognize_google(audio), srcLang, hi, callback);
#print(output)
            f.close()
