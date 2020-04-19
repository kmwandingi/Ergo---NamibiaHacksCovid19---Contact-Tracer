# Ergo---NamibiaHacksCovid19---Contact-Tracer

The tracer App uses your location history as obtained from google to plot a heatmap of your past movements.

To use (Windows Only): Make sure python3 or later is onstalled on your machine.

1.	Download repo to a local folder

2.	open cmd and navigate to the local folder you saved the repo through the command line

3.	In command line run: pip install -r requirements.txt

4.	After all requirements are installed: run: streamlit run CTracer.py

The app should open in the browser

5.	Go to https://takeout.google.com

6.	Download your location history (choose "json" format instead of the default "kml")

7.	Back to the app, choose desired date range

8.	Load your downloaded zip file into the app

A heatmap with layer controls and playback should open in a new tab.

