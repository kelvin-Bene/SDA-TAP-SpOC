# Meeting Transcript — April 9, 2026

## Participants
- **Bryant** (Project Lead / Facilitator)
- **Kelvin** (Developer)
- **David** (Developer)
- **Louis** (AFRL Scholars / Mentor / Stakeholder)
- **Dr. Cline** (Mentor)
- **Evan** (Student)
- Additional team members / mentors

---

**Bryant:** Let's use plan mode to outline exactly what the implementation of session three would look like. Again, ensure that we are addressing every single thing that is outlined in session three, and ensure that we are taking into account the work that we did in session one and two.

**Bryant:** Ensure that we do all of the research needed to ensure that this plan is as high and detailed as possible, work for as long as needed, use as many sub agents as needed. Ensure that you are working in a structured and systematic requirements.

**Bryant:** Anything's gonna be like a system requirements document. It won't be nearly as formal as a professional systems requirements document, but it'll be more than anything so to help make sure that we're on the right track.

**Bryant:** And then more than when we're passing it over, it'll be easy to glance and see what it is that we're missing, what it is that we been maintaining.

**Bryant:** And then we do also have our 2,000 appointments here. So should we answer things? Because that's the problem with that.

**Bryant:** Need to really iron out when it comes to the progress, to the new that we have. So before I get into anything else, I guess I'll pass it off to the students and more specifically maybe the development team. Would you guys like to show off the demo that we have going?

**Bryant:** Web application.

**Bryant:** Oh, when that means you. If you need another second to put up, let us know. David, do you happen to have that link? Probably best if Kelvin does it. I'm not too sure if he made any changes.

**Bryant:** Omi says his screen is lagged really bad. Alright. Okay. Hold on. Let me try to get up, see if it's currently loaded in.

**David:** Kelvin, are we showing the demo version or production version? Actually, I see that the demo version seems to be looking pretty good. So same URL. Alright. Okay. Let's give it try then.

**David:** Can everybody see my screen?

**David:** So welcome to our new UCB demo. You can see that we've integrated a lot of new UI features. So all this is pretty exciting for all of us. So as you here you guys can see, we have all of the original functionality with being able to generate datasets and also to submit our own UCTV processors to get a result from a data set. So how this works is, generally, you can come here into the generate data set portion after you add in your API key, you can select form of gene him, and all of the other parameters that go into the regular for generating the dataset. And then after doing this, you can go through, and you can go ahead and just basically generate whatever you want in terms of data. You can do lower orbit, medium earth orbit. You can do tip track jobs. You can select your date and everything works exactly as it would in the usual UDL.

**David:** Now after you finish generating your dataset, you can then go to a new submission, and then you can run the pause or wrap have output the results of your GCP. For example, if you use WCTP, you will be able to add the submission file here and then it's going to rate your overall result based off of this score, which is generally going to be based off the F1 square, I believe. And then from there, it's going to rank all of your different models and then tell you which one is better.

**David:** So all these functionalities obviously are not fully implemented on the demo. These are, like, you know, fake sentences and data. To actually test this, we would probably need some actual ECP. But overall, I mean, stuff is looking pretty complete. So I thought I would just open it up for questions or, you know, what you guys would like to hear about this?

**Louis:** This looks great. Can you walk me through the process? Like, start to finish, you open up this application you want to, make a dataset, save the dataset locally so you can upload it to your HTTP. By the time you ran it and then show me where you would upload your results and see the output.

**David:** Yeah. Sure. Okay. Wait. Hold on. Since everything got reset, my API key isn't in here anymore. Excuse me while I feel like you see all of them.

**David:** I'll fetch everything.

**David:** So basically, from the very start, obviously, you need a data set to work with. So here's where you would go into settings, and then would just go ahead and configure your UDL API key. Let's see if the save — oh, Kelvin, is the website up right now?

**Kelvin:** Yeah. I'm not sure exactly what it's doing. You shouldn't need the UDL key for the demo site since the data that the demo site's gonna generate is, like, it's synthetic data. It's not real.

**Kelvin:** So if you wanna show the whole process, either show the production site, right.

**David:** Okay.

**David:** Okay. This might be a little better.

**Kelvin:** And you can also start with, like, the landing pages instead of slash settings, it'll just be slash welcome. So if you just start with that, that'll, like, show, like, the landing page, and then you can go from there.

**Kelvin:** Thank you again, David. I really appreciate it.

**David:** Yeah. No worries. Okay. So I think I might go back to the landing page later, but since you guys were asking for general set creation. So let's just go ahead and let's just start from, you know, regular old generate data set. So let's say that I'm a researcher and I want to get a basic dataset.

**David:** Let's just use simple parameters for now. Low Earth orbit, and then unspecified object. Here's where you would essentially just make all of the requirements that you want for your data. Right? So let's say that I want, you know, two track jack, have target, hurricane. I want optical, and then I just want normal events.

**David:** Now I specify the dates, and here you can be pretty flexible with your date range. And then from there, you can now generate whatever objects type you want for whatever observation window you want.

**David:** Not sure what's the safest range for data. Let's just do one week, for example. And then see if we find anything. Oh, and there is different search functions also. Like, for the sake of time, let's just do the regular hybrid search for now, and then going to go ahead and enable downsampling and simulation in case they're needed.

**David:** And it is going to essentially generate a configuration and then let's name it "test dataset." For example, this is how you're going to find the dataset later. So now that we've figured out all of our different parameters, we can now go ahead and generate the dataset. And then — oh, no.

**David:** Seems like it does not like my UDL API token. For fun.

**David:** Why is — I'm so sorry about this, by the way. I didn't have a chance to practice things. Okay.

**Bryant:** Thank you, David, for being willing to—

**David:** Ok.

**Bryant:** Se dice?

**David:** Okay. Is the valid connection thing red, by the way? Makes me so nervous. But alright. Let's give this a try. And, yeah, so that seems to have worked. So the data is currently generating. And, essentially, like, as I said before, we are generating based off of what parameters we set. So if you just go back to UDL, for example, and then you look at wherever the actual query builder is. It's essentially the same thing. Whatever queries that you put into on UDL is basically just the same process here.

**David:** We're just querying the API to get the results onto the website. So it's functionally the same as just direct to the help pool.

**David:** So all that currently works except for downsampling and simulation, what happens on-site.

**David:** Let's give that a bit to finish. So after this process is completed, you would have to go ahead and go into submit. And then here's where you will hypothetically upload your submission file. Now none of us currently have an actual UCTB processor. So I just went ahead and then I just took the dummy UCTV that I had from a previous test. So let me see if I can find it.

**David:** Believe it was on Discord's number.

**David:** Alright. I think I might have found it.

**David:** So let's let this finish. Alright? So you see that this asset successfully finished. We have one dataset with a total of three objects, and then we have precise as well as the previews. And then here, you're gonna be able to download the dataset and then run this through whatever process you like. So let's go ahead and take a look at this JSON file.

**David:** Y'all see this, by the way?

**Kelvin:** No. We can only see the website. You need to share the entire screen.

**David:** Yeah.

**David:** Can y'all see my entire screen?

**Kelvin:** Yes.

**David:** Yes. So as you can see, I just — oh, sorry. Yes. Yeah. You're on the website right now. We see the website. Don't you just saw your ID pulled up?

**David:** Mhmm. Yeah. So as you can see, I just went ahead and finished generating the dataset. It mentions that it's LEO and a tier three simulated dataset.

**David:** And then I just went ahead and downloaded it, and now you should be able to view it inside of the actual code editor or whatever else we're using to process that. So for example, we can see that this is the PDS Hem and then it has the longitude and latitude, and then the optical, as well as just all of this. Although, it's a bit long, so I don't think we can preview all of it. But this is essentially the general idea.

**David:** You have a dataset which you first generate on the actual website, and then you download it so that you can run it through your UCT processor.

**David:** Once you get a result from your UCT processor, and we're assuming format, you would upload your submission files here. So here is an example of a UCT output.

**David:** That you could generate. So once it validates that everything is in the correct format, you can now — okay. Input the actual test datasets, test this against. And you can say, for example, that I am UCTP, Space Force. Let's say that this is Space Force UCTP, and then this is the first version of it.

**David:** And we want to run the test to see how it does. Now what you can do is you can submit this first evaluation, and after our time, it's gonna say, hey, did you finish your evaluation? Do you fail your evaluation? And then how did you actually do?

**David:** I'm not too sure how long this process is supposed to take. Kelvin, can you, like, you know?

**David:** But once this finishes, this is going to give you a score, and then the score is going to essentially determine how well you did. If you got everything right, you will absolutely have a 100%. And if you got everything wrong, you would have zero. So to reiterate, if you go through this entire process, you can generate your dataset, you can download it, you can run it through your own UCT processor, and then after you will submit your results for evaluation such that you understand exactly what's for you.

**David:** And then that is essentially the entire pipeline. I'll go ahead and wait a minute for this to finish, but then if it will finish whenever it decides to finish, I think. So I'm sure we can do for that. Oh, it's back to the again.

**Kelvin:** Yeah.

**Kelvin:** You gotta tell Claude. Alright.

**David:** But yeah. Okay. That's essentially the workflow for the website. What do you guys think? Looks good.

---

## Louis's Technical Feedback on Dataset Structure

**Louis:** So the evaluation that's running, more or less the same evaluation that was given to you at the beginning of the project. We didn't really work too much on that this semester. Right? Yeah. So if I remember correctly, the evaluation takes a while, mostly because the way that we propagated the covariance was with a Monte Carlo simulation with a large sample size.

**Louis:** We should probably be doing a linear covariance propagation, which would be, you know, take the ten thousand propagations down to, like, one propagation plus higher dimensional matrix operation, not important.

**Louis:** Can we go back to the data file, the output dataset that we downloaded and saved? I'd just like to take a look at that real quick.

**David:** Yeah. So the preview doesn't seem to be working because of how the format is, but essentially, the input looks something — sorry. The output looks something like this.

**David:** And it's just one single JSON string, and it's not very nice to look at.

**Louis:** Okay. So it's just one big string. So where is the — where is the data actually in there? Where is, like, the observations and the reference objects in this dataset?

**David:** I'm not actually too sure at the moment since it's so long. I mean, I'd assume that if we keep on scrolling, we'll eventually find the appointment.

**David:** Might take a while. Okay.

**Louis:** So for example, here's one — Observations is a key, and inside the key is a list of observation objects. And each element in the list is itself a JSON object. Is that what I'm seeing?

**David:** Potentially. We haven't actually gotten too sure about this. Like, I'm so sorry. Like, I'm not prepared for this demo. I probably should have, like, you know, practiced ahead of time. Like, this is why it's already on the spot, essentially. I'm not too familiar with it.

**David:** That's okay. This is a good exercise.

**Louis:** Yeah. So it does appear to be a list of — this looks like objects. Observations is a key in the outer JSON, and that's a list of yeah. Let's keep going, keep going further to see if we can get to the next observation.

**David:** I do believe you're right, though. I do believe this is just regular objects because, like, that's what you would expect to have from an output anyways. And I'm, like, because all this is straight from UDL. You know? Like, there's a limit to how creative it can get in terms of outputs. We know that it's always going to be data, whether it's going to be simulated or otherwise. Yeah?

**Louis:** Right.

**Louis:** So, yeah, I assume this would be very, very long.

**David:** But if we can scroll past all the observations to get to the reference, I'd like to see where — how we're looking for specifically for reference, I could probably just command it up and see if I can find it.

**David:** Spell it again. Sorry.

**Louis:** Yeah. I'm not sure what the key would be is the only thing. Yeah.

**David:** So it could be called reference potentially or something else, I imagine.

**Louis:** Just scroll, like, all the way to the end, and we'll work backwards.

**David:** This seems to be the very end. Then we have assigned object ID and track ID. Null. And then if we start going backwards, this still looks like more objects. So I'm not sure if objects are actually included in here, although this looks like a reference object, although I'm not sure. Cool.

**Louis:** I think that's — I think that's also an observation. Oh, that's also an observation.

**David:** Got it. Okay. I'm not sure if there are reference objects included in here then.

### Key Requirement: Separate Answer Key from Dataset

**Louis:** So it looks like we've got the list of observations. What we also need in the dataset are the state vectors and covariances for each one of the objects in the set.

**Louis:** So when you were showing me back on the front end, it said it made a dataset that had three objects in it, I think. I think it tells the number.

**Louis:** So in addition to the observations of those three objects, we also need to know a state vector and covariance that corresponds to each one of those three objects. That's how we're going to — that's how we perform that association.

**Louis:** Right? Because if we don't know the truth value of the state vector and covariance for each one of our objects, then we have nothing to compare the candidate estimate to.

**David:** Got it.

**Louis:** Now there's a bit of a nuance here because if we just take the list of observations, each one of the observations says like, one of the keys in this JSON object of each observation says, like, satellite number. It tells you exactly what number that is an observation of.

**Louis:** So in theory, this dataset is essentially the test and the answer key put together.

**David:** Got it.

**Louis:** If you had someone who was trying to game the system and get the highest result possible because they wanted to be on the top of the leaderboard for whatever reason — thought it would help them sell the product or something. Someone could take the list of observations, put together their output from the UCT processor to be the correct answer because we're handing them the correct answer.

**Louis:** So I don't know if there's a way to keep like, the list of observations and the list of truth values and state vectors separate but correlated in the back end so that when one downloads a dataset, they get just the list of observations. And somewhere in our file storage system, in the back end is stored the answer key, but we don't ever give the answer key away.

**Louis:** Right?

**David:** Got it. I believe that makes sense, and that probably would be, like, I think, okay to implement. I'd assume what will happen is we would just get this resolved. Right?

**David:** And then we would split it into the reference objects and then just regular objects. And then we would just keep the reference objects for ourselves on the answer key. And then when they input their results, we can just give them their results back without actually leaking any of the actual answers is my thought.

**Louis:** Right. So I think from what we have right now, the easiest way to implement that would be — keep this exactly the way it is. But then when you click on create dataset, it's going to make this, and then it's also gonna make a separate file that'll have a smaller JSON set that's just got three objects in it. It's got object one, state vector, covariance, time. Object two, state vector, covariance, time. Object three, state vector, covariance, time. And that dataset will be stored somewhere in the back end in such a way that the answer key points to the dataset and the dataset points to the answer key so you can't lose track of which one goes where.

**David:** Yes. But we don't give that to the person who's taking the test. Right? The teacher doesn't give the student the answer key.

### Data Minimization for Storage Efficiency

**Louis:** And then along those same lines — the observation objects here. There are several keys in that JSON object that point to a specific satellite number. So in the observation, there was a satellite number, and it gave the NORAD ID. And then I think there's another one that was, like, original object ID, and then it gives the NORAD ID again. Yeah. We wanna just remove those keys.

**Louis:** From the observation objects. And then if we wanted to make these datasets smaller and more manageable, we could go through and remove a lot of the extraneous information that we're getting in each one of these observation objects.

**Louis:** A lot of the keys, some of them were null. We can get rid of those.

**David:** We're not currently using any uncertainty information we can get rid of, like, sensor lat uncertainty.

**Louis:** All we're really using is the sensor latitude, longitude, altitude, the time of observation, the right ascension, the declination, the azimuth, and the elevation.

**Louis:** And then also it would be important to know which sensor. So, like, the sensor ID links into a specific telescope, for instance.

**Louis:** But by saving all of the metadata that we get from the UDL, our JSON file is gonna be huge. If we remove a lot of the extraneous information, now all of a sudden, it's a lot more manageable.

**Louis:** And right. Especially if we're going to be storing large amounts of datasets, every time someone creates a dataset, there's gonna be stored somewhere.

**Louis:** We're probably gonna want that storage to be as efficient as possible. So we don't want to save all of that extraneous information.

**David:** Got it. So okay. Yeah. It is a lot of stuff to keep in mind. Although, I do wonder if we're finishing all that in time since, like, we got, like, a week or two left before handover. This is going to be a little rough. Kelvin, thoughts on your end?

**Louis:** I'll just — just one thought on that is, you know, we don't have to implement all of these features. You know, this is a note for later. We've done a lot of great work here, but this is not, you know, a perfectly ready to go product as soon as we're done. We're probably gonna have another team to pick up where we left off who's gonna continue pushing towards the finish line.

**Louis:** Yeah.

**Louis:** So if we make notes on — if we had more time, this is what we would do. Kinda like what my team tried to put together for you guys when we wrote our documentation at the beginning of summer. If we had more time, this is what we would have done.

**David:** Yeah. That makes sense.

**Louis:** Something like that from this team would be great. Like, we wanted to do this. Man, no time. We thought about doing this, ran out of time.

**David:** This, this, and this would be cool features to have, that didn't advance us toward that minimum viable product, so we put it on the back burner, but you should look into it kind of thing.

**David:** Yeah. That makes sense. I'm doing this for project closing. So thank you. That's very helpful. I'll definitely keep that in mind, and then that way, the next team coming in, they'll have all this information, and, hopefully, they can work on that.

**David:** But, yeah, I mean, that was most of the presentation, I think. What do guys think of it? Is there anything else or any other questions?

**Kelvin:** Yeah. I mean, thank you so much, David. And thank you, Louis, for that information. That was great. Yeah. I got a little transcript of that. So I'll work on implementing that stuff. I mean, yeah. Don't know. It sounds like it'll be some changing of the data, but doesn't sound like it'll be, like, super huge. So I think I can definitely get that implemented. But I just appreciate, like, the framing and the guidance for this project.

**Kelvin:** Like, yeah, the way that you think about it is, like, definitely different than the way that I think about it. Because you have more of that background.

**Kelvin:** Yeah. So thank you a lot.

**Louis:** Yeah. Of course. Glad I can help. And I did see your email from last week. Sorry I didn't get a chance to respond yet.

**Louis:** It's been really, really busy on my end, but I did see that, and I was thinking a little about a short answer. I don't really think I know much about, like, technical infrastructure, how we deploy tools. But I'll see what I can figure out.

**Kelvin:** Yeah. Sounds great. Yeah. And no worries. I figured you were super busy. I've been slammed as well. So yeah, I appreciate it. Thank you.

**Bryant:** Yep. It looks great. And yeah, and I think as far as the deployment, yeah, don't have to worry about that now.

**Bryant:** I mean, you have the codebase which is great, and it's definitely come a long way.

**Dr. Cline:** You guys. I know this is all very useful. And I just wanna say, well, thank you to David for really diving in and being willing to showcase this work in progress for us. So was very exciting for us.

**David:** Yeah. Live demos are always interesting. It's great to have that skill practice.

**Dr. Cline:** Definitely. And especially since we weren't necessarily planning on it. I know last week, we had kinda briefly given you guys a little glimpse of what we had worked on. But thank you, David. I greatly appreciate you for diving into it.

---

## DGX Spark Discussion

**Bryant:** And, thank you, Louis and Dr. Cline, for providing such useful information. So now I would like to transition into something that had come up. We were wondering, Louis, if you and Melissa were aware that we were reached out to by Pete Dragniv and Dan Herlumen.

**Bryant:** Because apparently, I believe the Space Force has gone ahead and they bought a couple of these devices that we actually have here.

**Dr. Cline:** See.

**Bryant:** So, essentially, they're like personal AI supercomputers. And these supercomputers — they want us to upload all of the work that we have onto these supercomputers.

**Bryant:** And I bring this up because right off the bat, that kinda changes the behavior of what we have been working on a little bit. Because while we have been working on a web platform for dataset generation and evaluation, this is going to be more of a local thing. So, of course, worst come to worst, we were thinking we would just upload exactly what we have. But here are some of the things that we were considering when it comes to this DGX Spark.

**Bryant:** So one idea that we had, especially considering that we wouldn't have really much of a leaderboard given that it is local, would be maybe having both the website platform and some sort of downloadable evaluation tool.

**Bryant:** So this does pose a couple of different considerations and kind of points us towards different directions towards how dataset generation would work. So an idea that we had was to store the local datasets, potentially do some sort of encrypting so that — how you said, people wouldn't be able to necessarily access those datasets and make it look like they're using a UCT processor. It does a 100%. Maybe doing some sort of 80/20 kind of split so that the UCT processor actually has something to work on.

**Bryant:** We're wondering how we could go about potentially pulling data from the UDL. We don't know if the user would necessarily pull in the data.

**Bryant:** There's a lot of different things to consider, but I guess the main question here is — were you aware of this DGX Spark that popped up?

**Louis:** This is new to me. Like, I guess, what's the desired output or advantage of having this project on these personal AI Spark computers?

**Louis:** Just wanna understand without getting too much into it.

**Kelvin:** They just wanna be able to, like, deliver it to the project managers and have something impressive to show them that's, like, running locally on the computer.

**Kelvin:** Yeah. They said it's a new idea and a new thing for this year, just something that they're testing out. I don't know. It was something that was, yeah, sprung on us last minute.

**Kelvin:** I've already been working on getting a version that compiles on ARM64. Because that's what the DGX Spark is built on.

**Kelvin:** And, like, yeah, making it more of a local version. I don't know. It kinda sounds like just a side mission that was last minute.

**Dr. Cline:** From whatever.

**Louis:** If that's really just gonna be a storage mechanism where they can put it on here and then take it places and deploy it wherever they take it — I think that a local version of pretty much exactly what we have, where instead of uploading your solution to a remote server that has a leaderboard for everyone, each instance on each one of these DGX Spark units can have its own leaderboard, its own storage of datasets.

**Louis:** And this could be, say, each company or each squadron or each unit or whatever who's given one of these can have their own UCT processor benchmarking tool, and they can benchmark their UCT processors separately from everyone else.

**Louis:** So maybe we can do that. Wouldn't have to change functionality. We can just say, instead of being hosted on a remote server, it's just gonna be hosted locally. It'll function exactly the same way. It'll go grab data from the UDL. Store it, instead of on the remote server, it's stored locally. You upload your solution, which really wouldn't be much of an upload because it's all stored locally. You just kinda copy it into the application. It'll do the evaluation.

**Louis:** It'll store the results also locally on a local leaderboard. So instead of everything being pushed to a remote server that hosts everything, it'll just be stored locally.

**Louis:** Does that sound like a viable path forward?

**Kelvin:** Yeah. That's kinda what I started as is, like, I wanted to just get it compiling on ARM first and make sure there wasn't anything huge. So I have, like, DGX local edition. There's just like a couple visual changes I did.

**Kelvin:** I also set it up so it can run offline because I asked Pete — I was like, are they gonna have a UDL token? Are they even gonna have Internet? You know? Or are they just gonna, like, plug it into a TV and kinda show it off? So I bundled in a bunch of datasets with it already.

**Kelvin:** I also added a couple of AI features because, like, it seems like we weren't really leveraging the hardware very much. Like, it doesn't take that much compute to pull this dataset.

**Kelvin:** And it's, you know, like, it's on the GB10 chips, so 128 gigs of unified memory. So, like, you can query the database, you can explain your results, you can chat about the leaderboard.

**Kelvin:** And you can also, like, ask questions about your own upload of results. So just added in a couple additional features that'll just leverage that chip.

**Dr. Cline:** But yeah.

**Louis:** Yeah. I like the idea of initializing it with certain datasets. Because you're right. If this is being deployed somewhere with no Internet, they can't go make a dataset.

**Louis:** So along those same lines, maybe a nifty feature to have for these local instances would be — every so often, if it can be hooked up to the Internet, have some sort of sync that can go grab all or a subset of datasets that have been created on — if there's a constantly running remote server that has all the datasets stored or something like that.

**Kelvin:** That sounds like a great idea.

**Dr. Cline:** And I know — I mean, I hate to bring this up. I mean, I know we originally were hoping to deploy this on the SuperPod. But, yeah, a lot of things have been going on in the background. I can talk to folks about that and see if there have been any changes because it — this looks like it would be a great candidate to deploy on the SuperPod, so I will look into that. I can't make any promises.

**Bryant:** Yeah. That would be awesome, Doctor. And if you get anything, feel free to update us. That's a super awesome opportunity. So love to hear about it.

**Bryant:** Yeah. Because this is exactly yeah.

**Dr. Cline:** This is what we originally had in mind is to have something that could be accessed to pull the data, and to host the datasets. So anyway, stay tuned.

**Bryant:** Thank you. This is very exciting stuff. So hopefully, the local DGX — like we said, it looks like we're making some really good progress. Thank you, Kelvin, for that.

**Bryant:** But we'll see where it goes.

**Kelvin:** Of course. Yeah. This has been the first time where I'm actually thankful to have an ARM device because it compiles natively in ARM64.

**Kelvin:** Usually, ARM sucks for everything, but this time it's actually helped a lot.

---

## SDA Ecosystem Hosting & S3 Bucket

**Bryant:** K. With that being said, we do have roughly ten minutes left. So we did have a couple of questions. I know we already addressed this first initial one.

**Bryant:** Another one that we had was whether we're responsible for hosting on the SDA ecosystem. Depending on the answer to that question, we were still trying to see if an S3 bucket was necessary. And, obviously, the DGX part also provided some confusion for us. So do we know if we are responsible for hosting on the ecosystem?

**Louis:** I think the best way to get the answer to that question is when we're all out there at the end of the month for the expo and demonstration, we'll just go poke whomever, whether it's Major Allen or Dan or whoever and say, alright.

**Louis:** Here's that thing.

**Louis:** You asked us to build. What do you want us to do with it?

**Louis:** And the most likely answer will be either it'll be a very short task to take it and just plug it into the TapLab ecosystem, or they will take it and do whatever needs to be done with it so that it can be on the infrastructure.

**Dr. Cline:** Okay.

**Bryant:** That sounds fun. So we can have that exposition coming up very quickly. So I'm looking forward to it.

**Louis:** Okay.

**Evan:** I mean, it's like this — perhaps somewhat answered now that we've cleared up a little bit about how we may wanna go about this whole idea of local application on the DGX Spark.

**Evan:** But we were wondering exactly that — if we are gonna be needing that cloud data storage. We were looking at Amazon S3. I've been chatting with Melissa about it, but we temporarily put that on hold until we — I wanted to check in about the plans and if we're significantly changing stuff for this local functionality, which it kinda sounds like not necessarily. It's just we're doing a side branch as an option, but still trying to keep a lot of main functionality stuff that we've been working on for the past project.

**Louis:** Yeah. I would say we keep a lot of the same functionality and just deploy it locally.

**Louis:** It almost sounds like this DGX Spark is a pretty new thing that they were just, like, hey, here's this thing. So before we go around and make a whole bunch of changes to what we did to make it work with this thing, give them some time to figure out what they actually wanna do with this thing.

**Louis:** And then at that point, it won't be this team. It'll be someone else.

**Dr. Cline:** Yeah.

**Louis:** But at such a time when they have a better understanding of what they actually want out of this device and what they want out of our software on this device, then changes can be implemented if necessary.

**Evan:** Yeah. I think that makes sense, especially because we're so close to the end of the project term. Just finishing out with the same goals that we have been working with the whole time.

**Evan:** And doing whatever needs to be done to meet their needs of having this nice little flashy demo project on the local stuff. And then the next team can really deal with if there's gonna be a larger architectural transition.

**Evan:** That's their problem, I guess, and not ours. What we can do in two weeks.

**Dr. Cline:** Good.

**Evan:** Think that answers my question then.

---

## Project Handover Discussion

**Bryant:** Thank you, Evan. Thank you, Louis. While on the topic of the next team — and this is just out of sheer curiosity. I know it had come up when my students had asked if you guys were planning — do you know if you guys are planning on keeping this project on the Data Mine?

**Louis:** Just out of curiosity, I don't know about this project in particular. I guess it depends on where we end up and what's actually needed to push it across the finish line.

**Louis:** But as far as the partnership between DataMine and Kaplan, I'm fairly certain there will be either this or something similar regarding software and SDA where there will be another Data Mine team like you guys that are working on, if not this, then something similar.

**Louis:** That's exciting.

**Louis:** Okay.

**Bryant:** Well, thank you, appreciate that. So that was just out of sheer curiosity. We have five minutes left on the clock. Did want to go ahead and touch on passing work over.

**Bryant:** So do we know how we wanna go about passing this work over? Is there anything specifically that you're looking for that you make sure that you get?

**Bryant:** And by all means, feel free — don't mean to put you on the spot. So if you need to take some time and maybe make a list, feel free to.

### Louis's Handover Requirements

**Louis:** I'll give it some time to think it over but just off the top of my head for right now:

1. **Quick Start Guide** — Some kind of one or two page thing that says, first, creating a dataset: do this, put in your UDL token, click on this, here are your options. Click on this, this, this, click on this button to see your dataset. And then uploading and evaluating results — do this, this, this. Just a brief one or two page document that says this is everything you need to know to use this software without getting too far into the nitty gritty of everything.

2. **Full Documentation** — This is everything that happens in both the front end and the back end. This is how everything works. For if you're curious or if you do need to troubleshoot or debug something, you can dive into the documentation, but you don't necessarily need to familiarize yourself with the entire documentation to use it. Right? Like, how many of us have actually read the NumPy documentation versus we all use it every day.

3. **Transition Document** — If we had more time, what we would have done. Or this is currently an open hole in this system that hasn't been patched. This is a bug we noticed. If someone was gonna pick up this project — hand someone your codebase, hand them the documentation, give them the transition document that says:
   - The documentation will say "this is the system right now"
   - The transition document will say "this is the vision of what we wanted this system to be"
   - Features we wanted to implement
   - Suboptimal solutions (e.g., the Monte Carlo propagation takes a long time — this works, but it's suboptimal, it'd be better if we did a different kind of propagation)
   - Things that don't necessarily have to be broken that need to be fixed — could be things that work but are suboptimal
   - "Wouldn't it be nice if we had this?" — just put it down. Maybe someone will work on it at some point.

**Dr. Cline:** Yeah. I think that's great advice because this is your chance to sort of put it all out there. And the more you have in there about your vision and the future vision, I think you're more likely to attract more attention and follow-up.

### Lessons Learned

**Louis:** And then one more big thing that I just thought of — we should make a list of lessons learned.

**Louis:** What did we learn over the course of this project that would have made it easier if we had known? What do we know now that we wish we knew four months ago?

**Louis:** That's very important so that future teams or end users don't have the same problems that we did. If we can help someone solve an issue before it becomes an issue, well, that's great.

**Louis:** So let's get a list of lessons learned. What do we know now that we wish we knew sooner? Or what do we foresee might be a problem that if we can tell someone, they can make it not a problem.

**Bryant:** Alright. Hey there, students. Sounds good. Well, thank you, Louis. I'll send you an email. I'm thinking I'll forward you that email that we recently received for the DGX Spark so that you could see the information that we were provided.

**Bryant:** And then I'll also send an email asking about how we want to go about passing the work over. So could be code-based, and we'll make sure that we get all of this implemented and produced.

**Bryant:** And if you have anything else that you would like from us, the team, feel free to reply to that email. Alright.

**Louis:** Sounds good. Will do. Thank you.

---

## Closing & Continued Involvement

**Bryant:** Appreciate it. Students, before I jump into homework and some quick announcements, anything else? Mentors as well.

**Dr. Cline:** I mean, just to clarify something even though I think that's probably the case. So if I'm understanding correctly, none of us will be working on the project again in whatever incarnation it takes. Correct?

**Dr. Cline:** So, like, project's gonna be passed on and then none of us are gonna be involved anymore?

**Louis:** I'm not entirely sure about the whom or the where or the what — how projects continue or get passed on.

**Louis:** But if you would like to continue to work on this project, I'm sure we could find a way — a situation in which all of you can remain a part of this project.

**Louis:** Kinda like I'm still a part of this project even though I'm not directly working with or for TapLab anymore. We could keep you in the loop, or we could keep you engaged in wherever this project goes if that's something that you are interested in.

**Dr. Cline:** Got it. I think that'll be something that I will consider personally. Not sure about anybody else. But, yeah, thank you. Awesome. That's all I have. Thank you.

**Dr. Cline:** Yep.

**Dr. Cline:** I don't know how this process is supposed to work, but I think that's good is to keep your options open. And, again, if it's something you're interested in, that you're interested in it — that counts for a lot.

**Bryant:** I think there is also a lot in the air and maybe we might get some answers to that when the symposium approaches.

**Dr. Cline:** So yeah.

**Louis:** Sounds good.

**Bryant:** Thank you, David. I know I myself am very interested in this project as well. So a lot of students have worked very hard on what we've been doing. So I myself feel very invested.

**Dr. Cline:** Definitely. And I certainly appreciate all the hard work you all put into it. It shows.

**Louis:** Thank you.

**Bryant:** Thank you. And I appreciate you mentors as well for bearing with us and answering all the questions and confusions that we have. So it's definitely made this a lot easier.

**Bryant:** Going once, going twice. Students, mentors, anything else?

**Dr. Cline:** Okay.

**Bryant:** I know Kelvin said he'd be very interested in getting this deployed on the SDA TapLab system. So likewise. I would concur with that.

**Dr. Cline:** I would yeah, just love to see it in action at the TapLab.

**Bryant:** Okay. Really fast then. So just make sure that we're continuing to work, continuing to collaborate. I know we touched on a lot of useful information today in our meeting, so keep that in mind. Maybe start thinking, get those gears moving. Any ideas that you guys have for any sort of progress, make sure to write it down. Feel free to throw it into the Discord or throw it into the questions and concerns document.

**Bryant:** I would like to remind us that the project closure assignment is due April 24. Also, there is that challenges document from Rachel.

**Bryant:** To have us all fill out. And if you haven't already, please fill out that poll that is within the expositions channel or Discord to confirm your attendance. Okay?

**Bryant:** But with that being said, you guys know how to reach me, and I don't wanna hold you all longer. I'll hang behind if we have any questions or would like to chat.

**Dr. Cline:** Likewise. Thank you, everyone.

**Bryant:** Thank you. You, David, take care.

**Dr. Cline:** Alright. Thank you.

**Bryant:** Thank you, guys. Thank you, Louis. Thank you, talking to everyone.

**Kelvin:** Thank you again, dude. Shout out.

**Dr. Cline:** My laptop is — I get it.
