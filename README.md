# Netflix Blendz

**Project Description**
Have you ever struggled to find something to watch on Netflix with your friend? Well, Netflix Blendz has just the solution for all you indecisive couples/pairs out there. Netflix Blendz is a webapp that allows two users to upload their Netflix user watch history to generate a custom list of recommended movies titles that you can enjoy together. A blend of your viewing tastes if you will.

**How to Use the Webapp**
To generate a Blend, simply upload a csv file of your Netflix watch history. Here are instructions on how to access it:
    1.  Log into your [Netflix account]("https://www.netflix.com/")
    2.  Go to your Account page
    3.  Open the Profile & Parental Controls settings for the profile you want to see 
    4.  Open Viewing Activity
    5.  Select 'Download all' at the bottom of the page to download your watch history as .csv file

Once you have your csv file, upload it to our database with a unique identifying username! To create a blend with your friend, enter both usernames and select "Find Your Blend!"

**Repo Organization**
* `Netflix-Data` contains datasets with of Netflix movies that were used for the reccomendation system.
* `Webapp` contains html templates, css files, and the app.py file with functions for the web application.
* `recommendation_system` contains code that was used to develop the recommendation_system.

