# Feb 19, 2026 Meeting Transcript

Bryant Ortega
Alright, how we all doing?
It's nice to see everybody again.
It's nice to see you, Louis.
Louis Caves
00:00:19
Hey everyone, how's it going?
David Xiao
00:00:25
We are working, and we had a lot of questions.
Louis Caves
00:00:29
Things are good.
Bryant Ortega
00:00:31
Yeah. I, did you get a chance to look over the Google Doc, Lewis? I was just planning on, pretty much today doing kind of, like, a stand-up style, going through, like, the Google Doc per team, sort of.
Louis Caves
00:00:45
Yeah, I briefly looked at it.
Bryant Ortega
00:00:48
Awesome.
Sounds good. Yeah, we wanted to make sure if you wanted to get a head start or anything, I'll give you that opportunity.
But, alright, well, I hope everybody's doing well. I know Kevin's gonna be a couple minutes late.
So that's okay, but we'll go ahead and get started, okay?
In general, we kind of just kept working. I know we have started working on, like, our poster, we kind of started setting that up, but really, just within our own sub-teams, we've all just continued to work, continued to tackle the tasks that we've all kind of identified.
But, I guess we'll start off with the data ingestion team.
I know Calvin normally runs that, but James or anybody else from the data ingestion team, I believe Zakiya and Kara are in that team as well. Do you guys want to go ahead and do a quick little stand-up?
Progress, roadblocks?
james
00:01:49
Yeah, so…
I'll start with, like, the roadblock we were working with first. The dashboard, we couldn't get it to generate a dataset for either of the three options, the
fast hybrid and windowed version. So I played with it in the repo that I cloned, and changed the query from the UDL to fall back on observation time rather than satellite number.
And then from there, I got some data to be generated, so that's good. And then, as far as other stuff goes, I can only speak about the simulation portion.
But the goal for me and Patrick was to get some data, look at it, and see, like, what kind of missingness there is, like, at random or correlated and whatnot. And then from there, we can kind of research what imputation or simulation methods might be best suited for those.
So we have kind of, like, a rough week-to-week plan for that.
Louis Caves
00:02:49
Okay, so you had mentioned, like, the first thing you'd mentioned, you changed the UDL query from a satellite number to an observation time? Could you comment a little more on… on how that… or, like, what you mean by that?
james
00:03:04
Yeah, so, at least from what I was…
understanding, like, the… the call for the satellite numbers, it would just keep coming back with an error that said, like, satellite, let's just say number 1, right? Wasn't available, or something like that. And…
from what I was… Guessing or gathering,
Might be because either the code itself wasn't pulling correctly, like the query itself, Or there just wasn't,
observations available for the selected date ranges we were doing, but instead of kind of doing, like, a…
let's see when there might be data available for that. I just said, maybe we can do something where it's, like, get any satellite from this time range instead.
Louis Caves
00:03:53
Okay, yeah, so if you're trying to… if we're trying to query specific satellites and there's no observations in the… in the time for that satellite that we're trying to look at, then it would… the query would just come back with, like, an empty set.
james
00:04:06
Right.
Louis Caves
00:04:06
So I guess that raises the question of when, like, in what instance are we looking at querying observations for a singular satellite, as opposed to what you had mentioned, pulling observations for
many different satellites over a given time range, because when the user is inputting his parameters, he's not going to necessarily say, I want to see this satellite, this satellite, this satellite, this satellite. We're not going to have that list of satellites a priori. What we're going to know is the user wanted data
that span this length of time. So I think that looking…
add a time window and pulling all of the satellites, or some subset of the satellites, from that time window is probably a little more useful than pulling observations for a specific satellite number. The, the exception being if we add, like, some kind of special, like, debugging
type data set, where it is hard-coded what satellites we want to pull that are, like, quote-unquote calibration satellites. So you can look at the same satellites every time that have very well-known or very, very well-tracked position. We could have a list of those objects, but those objects would have to be picked out
just specifically to avoid the problem that you're talking about, where there's no data available at any given amount of time. So, I think we should probably be pulling based on time instead of a satellite number anyway.
james
00:05:36
Yeah, right.
Kara Mccormick
00:05:38
Something to add on to the ingestion team, I was looking into, like, how we could use AI and stuff, and, we were talking about using other, databases, like, just not, not just the UDL, but, like, maybe, like, the ESA and other ones.
And I thought maybe it could be cool to, like, use AI to, like, compare and contrast the data and look for, like, differences and anomalies, just to make sure that it's, like, constant before we plug it in.
Louis Caves
00:06:11
Yeah, so there are other sources of data that would probably be able to give us
like, an orbital estimate, like either the TLEs and or state vectors with covariance, that…
ESA database is particularly useful because they'll give us mass and cross-sectional information for each one of the satellites, which is needed for the orbital propagation the way that we're using it. So we're going to need to pull at least mass and cross-section from,
the ESA as well.
And then for calculating things like the orbital coverage, which is one of the data quality metrics that we're looking at, we're going to need to know approximately the orbital elements
specifically the eccentricity and the semi-major axis, so we can pull that data from either the UDL or ESA or, any other
publicly available databases, but to the best of my knowledge, I think the UDL is going to be our only source of observation data.
That may not be correct, if we can find…
Raw observation data from another source, then we could definitely, you know, see if we can use that as well.
But I think that the UDL is probably going to be our main source of observational data, so we should…
you know, continue trying to work with, you know, optimizing our UDL queries.
Jon Cline
00:07:43
On that, I mean, that was… that's… that's an excellent suggestion to use AI for some of the data analysis. One of the things you could do is pull the data, the UDL is going to be the data source, but pull in a snapshot, and then…
And then use… you can build up AI agents to do some of the…
the data cleaning and data analysis. So, just…
That's where, if you get it in a database…
like, such as DuckDB, there… just… as long as you have an MCP, connector for that particular database, because that could be a really quick way to do it.
So, get it in a form where you could easily then talk… get it to talk to a, talk to an AI agent.
And then…
Yeah, that would be looking into how you could train, you know, train an agent, look specifically at these types of data sets. I can see how that could be useful.
Bryant Ortega
00:09:04
Thank you, Dr. Klein.
Data ingestion, you guys have any questions, anything else you guys would like to bring up?
No, we already addressed the questions that are on the Google Doc.
Okay, sweet. I'm gonna go ahead…
And… move on to the next…
Team, then. We've got, data storage.
So, for data storage, essentially right now, we're still kind of getting a grip, but kind of still understanding the actual pipeline. We're trying to really track everything from data ingestion to data storage. So, I know…
we're looking into Kelvin's code, kind of trying to see how Superbase works, kind of trying to see how,
everything else is implemented, I know there's Postgres in there as well, so we're mostly trying to create documentation on that, but we are getting ready to start implementing,
Douglick.
We're getting ready to start implementing Duck Lake, and then, also looking into MongoDB currently.
So, yeah. That's where we're at, but we don't have any questions for now.
Unless… my team members, before I move on.
Ruben Vipinraj
00:10:27
Not me, no question.
Bryant Ortega
00:10:32
Awesome, sounds good.
Thank you.
Then, we'll go ahead, we'll move on to UCTP analysis.
I did go ahead and I pasted the questions on the slide, just in case y'all needed a reminder.
David Xiao
00:10:47
Yeah, so for our team, like, we have made some progress and sort of, like, you know, wrapped our heads around basic plans, and right now, what we are trying to do is we're trying to acquire
from either you guys or from another source, a UCCP processor, and we thought, like, in the meantime, we'll work on it ourselves, since, like, you know, there's no guarantee that anybody else can respond. And also, we kind of need a very shitty model.
in order to simulate what happens if you have a bad processor, you know? So, like.
We want to have a sanity check and make sure that our model isn't rating a bad model as a good model.
And currently, like, we have a very big roadblock in that we don't really, like, you know.
we don't really understand where to start in regards to this. So, I know that, Lewis, you sent a member of our team, Zaka, like, you sent her an email with some of the UCCP analysis stuff, not sure if you have it at the moment, but currently, what we kind of need are, like, you know, we want to know what inputs are… outputs are necessary for the UCP benchmark, and like, you know, what each field within that is supposed to mean, like, how we're supposed to calculate it, that sort of thing, like, you know.
Right now, we're just kind of in a situation where there's a ton of data that we need to get processed, but we don't really know how to, like, do any of those calculations. So anything that you guys have, like, in terms of libraries, in terms of…
User guides and documentation would be super helpful.
Also, we currently also need, like, an example of input and output, and, like, a good result and a bad result, basically, like.
We need to see, like, you know, what looks good in terms of having a good model, and then what looks bad in terms of having a bad model, since otherwise we're kind of just, like, taking shots out of the dark over here.
Currently, I know, Louis, that you sent something our way earlier. I believe that you had, like, one input and one output, but they seemed like they were different things. Like, the input was not connected to the output, so we were a little confused about that, and we were hoping for a little bit of clarification.
Also, like, we just want to know, like, you know, do we think that this is reasonable for our scale level? Like, is this a productive use time? Because as it currently is, the team's a little demoralized, we're wondering if we're ever gonna make any progress on this, you know?
Louis Caves
00:12:45
As far as the inputs and outputs, we can go through, and I can show you what, you know, what the inputs are, what each one of the fields are, what the outputs are, what each one of the fields are.
Is whomever is sharing their screen, do they have…
The documentation pulled up, or do you want me to share my screen, or what, what's easiest?
Bryant Ortega
00:13:08
I can go ahead and pull up the documentation. Let me just make sure it's the one that we're thinking of.
Whatever you think is easiest, Louis.
Louis Caves
00:13:33
Alright, so let's see, do we have a copy of any one of the sample… sample data sets?
Do we have a sample data set anywhere?
I can probably…
David Xiao
00:13:46
I mean, like, the tin object stuff? I could probably upload a few in chat, although I'm not sure if anybody will be able to read that. It's a bit… weird.
Brian, if you want to look at Discord, I think I have some in our team channel.
Bryant Ortega
00:13:57
Okay.
I'll go ahead, I'll take a look at that.
David Xiao
00:14:01
It might be easier for me to just send them to you, hold on.
Did you get the pink?
Bryant Ortega
00:14:16
Yes.
Okay.
Do you want me to open these, or do you want to share your screen, David, or…
David Xiao
00:14:34
Actually, on that thought, yeah, like, maybe me sharing my screen would be more efficient.
Can everybody currently see my screen?
Louis Caves
00:14:47
Yes.
Evan
00:14:48
Yep.
David Xiao
00:14:49
Alright.
So currently, like, we got the 10 objects dataset that you gave us, and, like, it was pretty self-explanatory. I think, like, this sort of data is what we would expect, typically, from UDL. And then, I ran it through, and I… what I did was…
I went ahead and recoded the dummy UCCP so that it just directly outputs the results to HSON file, and, like, this is the results that I got. We also had the results that you gave us from UCCP output, although it looks like, like.
I think this was for a different dataset than the input.
But we were a little confused about stuff like this. So, in terms of source data, source data was just the different observation IDs that were inputted, correct?
Louis Caves
00:15:33
Yes.
David Xiao
00:15:34
Alright.
And then, source data types, EO, we assumed that this was Earth observation, so this could mean, like, LEO, GEO, anything like that.
Louis Caves
00:15:42
So, just… just to correct a quick misconception that doesn't actually matter, EO stands for electro-optical, so that's a telescope observation. So that… that would be, like, replace that with radar if it was a radar measurement, or RF if it was a radio telescope.
David Xiao
00:16:00
Got it.
Louis Caves
00:16:00
These were all, electro-optical observations, they were all made by a telescope. But, moving on.
David Xiao
00:16:08
To what extent does source data type matter, by the way?
Louis Caves
00:16:12
It would only matter if we had a dataset that was composed of different types of data. Right now, we're only looking at EOs, so that.
David Xiao
00:16:20
So everything should be equal.
Louis Caves
00:16:21
Absolutely nothing.
David Xiao
00:16:23
Got it. Alright, and then classification marking. So, what does this mean exactly?
Louis Caves
00:16:29
That does not mean anything for us. That is who created it. This was the output from the UCT processor owned by the corporation LSAS. You can see that somewhere in there, LSAS. They… this was… this was an actual output from their UCT processor.
David Xiao
00:16:49
Got it.
Louis Caves
00:16:49
I can't say what all UCT processor outputs will look like, but I can tell you for a fact this is the output for a UCT processor that is currently
Outputting data.
David Xiao
00:17:01
Got it. So this would be, like, this would be a satellite, potentially, then?
Louis Caves
00:17:06
No, that is… Essentially, it's a different type of label. It doesn't actually carry any data.
David Xiao
00:17:15
Got it.
So, like, one of the big confusions that we had is, suppose that we made our own UCT processor, right? Like, are we following these sort of fields exactly, then?
Like, what would… if we were to create classification marking, what would we want it to look like, for example?
Louis Caves
00:17:32
I mean, you could… you could have it say, I don't know, like, U slash slash Datamine of the Rockies. You know, it's… Oh, so this is just a label for the organization? It's just a… it's just a label, yeah.
David Xiao
00:17:43
Got it.
Louis Caves
00:17:43
So, LSAS, that was the company that created this output.
So their classification marking is saying this was generated by the LCAS processor.
David Xiao
00:17:58
Okay, I'll leave that in a note for later. And the epoch is the time epoch, I think we got that, and then obviously all of these are UCTs.
Okay, X position, Y position, Z position, and the levels and stuff. So, like, was this directly pulled from the source
Horsada, like, is this the exact same…
Location values, or is this something different?
Louis Caves
00:18:17
That is something different. So, remember what the UCT processor is trying to do. It's taking in a sequence of observations, right? So, all it… all it gets is, if you're gonna,
Go back to the, the 10 objects dataset.
David Xiao
00:18:34
Yes.
Louis Caves
00:18:35
So, right at the top, dataset Ops. This is what goes into the UCT processor. It sees a list of, you know, ID, op time, ID sensor, azimuth, elevation, range, etc.
So…
it… that… that's all the processor gets to know, is that list. So there is no… there is no state vector being fed into the UCT processor. So if you want to collapse the datasetOps portion, click on the little drop-down arrow right next to…
Yep. And now, reference, this is the part of the dataset that's not being given to the UCT processor. This is, if the dataset ops is the test, this is the answer key. This is what's withheld by the benchmarking software to evaluate the UCT processor output.
So, the reference is saying.
within this dataset, this dataset was composed of 10 objects. Within this dataset, there are these 10 objects, so there should be 10 entries in the reference section. It's saying the satellite number, that's the number of the satellite, it's giving the position and velocity, the covariance, the epoch.
So, those are the 10 objects that exist within the dataset.
What the UCT processor is doing is it's going through the dataset OBS, and it's trying to find as many different objects as it can inside of that dataset. So, if the output of the UCT processor was to be 100% accurate, the output
could match what is in reference. But since it's not going to be 100% accurate, the output that you see in… go back to UCT processor output.
the output that you see here, the position and velocity, isn't going to match exactly what we see in reference. So what we're looking for is we're going through each one of the outputs in UCTP output, and we're trying to match which actual object it's closest to.
Once we do that, then we have the correlation between… because in this output, it's not giving us a satellite number, it's just saying, I found something at this position. It doesn't know what it found, it's just saying, given the observations, I think there is something here.
So we take the list of some things, we call it candidates, we take the list of candidates from the UCTP output, and then we take our list of references from the dataset, that second half of the dataset. We find which one of the candidates
are closest to each one of the references, and then we say, this candidate is most likely supposed to be this reference. Now that we have the correlation between
candidate and reference, then we can go through and say, for each candidate.
we look at that list of grouped ops that says, in the output.
So, in the output, right, there is…
if we go… go up above source data type, where there was the list of IDs, so yeah, this… this right here. This list of IDs.
That corresponds to the IDs from the dataset that it was fed into the UCT processor. This subset of those ID numbers is all of the observations that the UCT processor used
to generate that candidate. So it's saying, based on the observations, I think there's a thing at this bot.
I think there's a thing at this spot, because all of these observations correspond to that thing.
So… This source data type
or the source data, that's the list of observations that the UCT processor thinks is associated with the objects.
Back in the dataset, part of the reference is, you know, the similar, similar feel to that. So…
Yeah, if we scroll…
Oh, scroll down past that one, that one… yeah, right, right here, grouped ops ID. That's…
the same list of IDs that we're seeing in the UCT processor output. So, the output of the UCT processor could look similar to the reference section of the input, but the UCT processor output is not going to be giving us
a list of observations. It ingests the observations, and it outputs the list of candidate Objects and steep vectors.
So, when we go to make the dummy UCT processor, which is useful for trying to, you know, verify that our algorithm actually, you know, runs without error, it's not going to tell us whether, you know, what we're seeing is actually correct, it's just going to…
Say, you know, whether we wrote
essentially just runs without an error, runs to completion. So, the dummy UCTP is going to take in the dataset, that first part of the dataset that's labeled datasetObs. It's going to output something that looks similar to
that reference section in DatasetOps, or looks similar to…
the file that's called UCTP Output.
David Xiao
00:24:14
Got it. Okay, hold on, that was a lot of information. So…
Sorry, can I ask you to clarify some stuff? So essentially, what… so what is the processor that
trying to do at a very high level in that case. So, like, are we giving it a bunch of observations, and they're saying, oh, all of these observations are this object?
Louis Caves
00:24:34
Yes. Except there's going to be more than just the one object.
David Xiao
00:24:38
Got it. Right.
Louis Caves
00:24:40
Right.
David Xiao
00:24:40
So it's going to try to correlate multiple objects. Sorry?
Louis Caves
00:24:44
Yeah, that's exactly what the processor is doing, is suppose, you know, we're looking… you were looking at
you know, stuff orbiting around the Earth. There's going to be something orbiting, you know, very far away, something orbiting very close, something orbiting very eccentric, and you're gonna see it at a bunch of different spots. You're not gonna see the whole orbit, you're just gonna see a bunch of dots.
And what the processor is going to do is it's going to try and draw those orbits to fit as many of the dots as possible.
And the output is going to say, I drew these orbits, and I used these dots to make this orbit. And when we evaluate, we're going to say, well, how close is that orbit to the actual orbit, and how many of those dots were drawn on the correct orbit?
David Xiao
00:25:31
Got it
So, in those terms, then, all of these observations were made with a few reference objects in mind, is that correct? So basically, we picked different observations with different reference objects, and now we're trying to see if they guessed the correct reference object.
Louis Caves
00:25:47
Yes, we as the dataset builders, selected the reference objects, and then we give that to the UCT processor. The UCT processor, as the one that received this set of observations, they're trying to say, based on this set of observations.
I see this many objects in this dataset. And then we take the list of candidates, how many objects did the UCT processor see, and we compare that to our reference, which is how many objects did we actually put in there.
And then we can compare and see how close are those two. You know, a better processor more closely matches what was actually put in the dataset.
David Xiao
00:26:31
Got it. So basically, we start with certain, reference objects, let's call them R, and we… let's say that this is the Earth, and we know that the reference objects follow so-and-so orbits.
And then, right now, there's different points, on which…
we see those observations because we don't really see all of them. So, all these yellow dots basically get sent over to the UCC processor.
And the processor's gonna look at these dots, and then they're gonna say, well, I think that this observation corresponds to this object, this observation corresponds to this object, etc. And then, at the very end, they're gonna give us back
What objects they think they found, and then we need to evaluate which one is correct or not.
Am I understanding this correctly?
Louis Caves
00:27:20
Essentially, yes, but there are a couple of more nuanced things. So…
Everything was right up until, like, where you drew those arrows. The, the UCT processor isn't going to say, I found objects with satellite ID number, you know, 12345.
Yes. Right, what the UCT processor is going to do is essentially, you know, if you, like, draw a line between, you know, what you drew here, and then into the UCT processor, it's just going to see a bunch of dots.
David Xiao
00:28:02
What does it do with these dots, then?
Louis Caves
00:28:05
Here, hold on. Let me see if I can…
Let me… let me see if I can share my screen real quick.
David Xiao
00:28:14
Yeah, yeah, I'll stop sharing mine.
Louis Caves
00:28:25
Perfect.
Sure.
Hold on.
Sarah.
David Xiao
00:28:51
Yeah, no worries.
Louis Caves
00:29:05
Great.
So… You had… You know, a bunch of things.
orbiting the Earth, right?
And they could be… So, we get…
A series of observations, and each one of these observations
Calls on one of these orbits that we have put into the dataset.
So…
this… the observations go into the UCT processor. The UCT processor doesn't get to see these lines, all it gets to see is, you know.
here's… Oops.
Here's the Earth in the middle.
And then… Here's all those observations that we just took.
David Xiao
00:30:02
Yes.
Louis Caves
00:30:02
Yes. So, what the UCT processors are trying to do now is it's trying to say, based on these observations, I see
this object… this object… this object, and this object. And it's saying, based on…
So, this is the information that it's giving back, is this object here is defined by a state vector, which is your list of your X position, Y position, Z position, X velocity, Y velocity, Z velocity.
So, that's why it's giving you a list of, you know, this information, is this defines this orbit, that it's saying, I think I see this thing. And I think I see this thing because,
This observation, this observation, and this observation all correspond to this.
thing that I think I saw. So, in the list of…
source data type, or grouped ops, corresponding to this state vector, it's going to give you the ID numbers of
This observation, this observation, and this observation.
So, essentially what you were saying is correct, but…
where you said it's going to tell you which objects it sees, that's correct with an asterisk. It's not going to tell you I see satellite number…
you know, XYZ. It says, I see… I see a thing in this orbit. So, the way it's going to tell you what object it sees is…
It's going to give you this state vector, the position and velocities.
So, because the processor doesn't actually return,
a satellite ID, the same way that we chose a satellite ID to put in the reference object, or the dataset of reference objects, the first thing that we're gonna have to do here is…
Let me see if I can…
First thing we're gonna have to do here is, you know, say this is our reference, and this is…
or, you know, this is our reference, and this is the UTT processor output. The first thing we're gonna have to do here is, well, does this…
Orbit? Is that supposed to correspond to this guy, or is that supposed to correspond to this guy?
So what we do is we take this state vector, That defines this orbit.
And we're going to compare it to the state vector of this guy, And… this guy.
And if, you know, X is… Closer to X1.
than X is to X2.
then we're going to say that X is…
X1, because it's closer, and that means this other guy is X2.
So, we have to go through and figure out, you know, based on the list of candidates, which reference is supposed to go with which candidate. And then once we know that, then we can start evaluating, well, how close is the state vector X? Did they group
the correct, you know, observations. Were these observations all supposed to go with this guy, or was this observation supposed to go with, you know, this one? So we can't perform any of those metrics calculations until we first know which candidate is supposed to go with which reference.
David Xiao
00:33:57
Got it.
Okay.
So I think I understand all of that, and then… let me see if I can draw it out again.
Okay, so everything up until that point, we know that we already have, say, a list of different orbits, so let's say that we have
Orbit 1?
Orbit 2, and then… Suppose that we had, you know, 3 different reference objects.
So now what we need to do then, if I understand you correctly, we need to compare all of these, and then figure out which one is supposed to be which. So, like, let's say that O1 looks like this, then we'll say that O1 is equal to R2, and then… and now we compare these and see, like, how much the residual is.
And then, like, the goal is to have a residual of zero, hypothetically, if you got it perfectly correct. Does that… is that correct?
Louis Caves
00:35:05
Right. So, the way that we actually do it, because we have, you know, many candidates and many references, and possibly not exactly the same number, what we do is we take, you know, 01, and we compare it to each one of
R1, R2, and R3. Then we take O2, and we compare it to each one of R1, R2, and R3. And then we choose an association between the O's and the R's that minimizes the global error. So that means, you know.
O1 might be closer to R1 and R2, but if it's really, really far away from 1 and only kind of far away from the other, right, we want… we don't want to just look at
you know, O1 is closest to R1, but if 01 goes to R1, then R2 and R3 are all really far away from everything else. If…
you know, there could be a situation where, you know, we put an O with an R that isn't locally minimum to that one, but it's globally minimum to all of them. So we want to associate, you know, each one of the orbits to each one of the references, such that
the total sum of the errors between all combinations is minimized. But yes, that is how that works, is the first thing we do is we match the orbits to the references.
Evan
00:36:27
search.
Are you doing, like, an RMSE between, like, the orbits and the references?
Louis Caves
00:36:34
Yeah, so,
Rmse would actually be, like, some kind of, like, a sum over residuals. We're just comparing the state factors, so that would just be, that would just be a Euclidean norm. So, like, the magnitude squared of each one of your components.
Evan
00:36:51
Okay, okay, that makes sense.
David Xiao
00:36:54
Yes. So that said, okay, wouldn't this put a lot of demand on the accuracy of the model then, since, hypothetically, suppose you have, like, you know.
Three orbits that are, like, completely off.
Wouldn't they hypothetically map to the wrong observations also?
Or, like, sorry if I'm being a little unclear.
Louis Caves
00:37:13
Yeah, yeah, so if…
If the orbits that, you know, it spits out at you are all very far away from
you know, the reference that we put in, then that initial association probably isn't going to be great. Yeah, that's… that's correct.
And if… the…
initial association isn't great, all of the subsequent metrics that rely on those orbits being close are probably not going to be too great either. But that's not an issue, because if that initial association is not good, the underlying processor that gave you those outputs is not good either.
Which means that we're not losing anything by subsequently failing all the evaluation metrics, since the… we know the initial processor is not good to begin with.
David Xiao
00:38:08
Yeah, so garbage in, garbage out. If it's bad to begin with, it doesn't really matter if it messes up later.
Louis Caves
00:38:14
Exactly, but if we provide our valuation pipeline something that has the appropriate fields, and has, you know, the right number, or the
You know, all the right fields that we're looking for to actually perform the orbit association followed by the calculation over subsequent metrics, and actually give us some sort of final output.
then…
it's a garbage output, but that's all… that's a way to verify that we do, in fact, get an output, and that our pipeline can run to completion. So that's what the dummy UCTP was, originally, was it was supposed to be
Put in a dataset.
It's just going to, you know, jumble it up, completely randomized, and it's going to spit out in a format that you can plug into the evaluation pipeline for, not
You know, a final validation, simply just, like, a verification that
you know, the algorithms will actually work without error. There's no, like, critical bug that prevents anything from running.
David Xiao
00:39:21
Right. So, I guess then I should probably ask for, like, more practical applications in terms of tasks then, and, like, sorry if I'm taking up everyone's time. Does anybody else have a question? I'd be happy to stop here if you guys have something pressing that you want to ask also.
Aidan Schlesinger
00:39:37
It's not super pressing, I guess, but, I know Brian wanted us to include some sort of AI into the…
UI.
David Xiao
00:39:47
You should probably go first, then. Like, go ahead and ask that before I continue, because, like, if I continue, all our time is gonna be gone.
Bryant Ortega
00:39:54
Okay, yeah, I can go. Yeah, so I guess… Can we go ahead and do, like, a stand-up if you want, maybe do a little progress, kind of where you guys at, and then ask a question?
Yeah.
Aidan Schlesinger
00:40:04
So we have…
updated the UI, so, I ran out of tokens, I can't actually open that right now.
But…
We have edited it a little bit, so there's, like, a globe, sort of, just some, like, fun UI, sort of more interactive stuff.
So that's sort of where we are with that.
The question is, I guess, like, to incorporate… incorporate AI,
It's, like, a chatbot or something.
That you would be interested in using to, like, maybe find specific
I guess, results, or, I guess, help navigate through, said… AI for new users.
Louis Caves
00:41:02
So, like, what would… what would this AI be… be doing? What would… what's the…
what's the designed output for adding this functionality? What are we… what are we expecting to gain by adding an AI into our user interface?
Aidan Schlesinger
00:41:21
I… It could be as simple, I guess, like, if…
The user is having trouble accessing or finding Or navigating throughout the website.
Like, just asking at the… Like, a question or something to help out?
Or, like, going and finding more specific, I guess, results.
Louis Caves
00:41:45
I mean, then, yeah, sure, if that's, if that's something that we…
think should be a part of the functionality of the N program, then… We, we definitely could.
I don't know if it… would…
be necessary to, the functionality of the product. It might just be, like, oh, that's a kind of, like, cool-to-have thing at the end.
But I don't know if that necessarily helps advance the project towards our minimum success criterias. So…
We… we can… we can think about how we would want that to look, once…
You know, we get the backend pipeline functionality working.
But I don't know if that's…
Necessarily the best focus of our efforts at present.
Aidan Schlesinger
00:42:47
Okay, yeah, that makes sense.
David Xiao
00:42:54
Was there anybody else, by the way?
Jon Cline
00:42:59
Oh, I was just gonna make a comment on the AI. I would consider that that would be kind of like icing on the cake, but we'd need to focus on the cake.
But that said, it could be useful going forward, just sort of imagine,
you're training an agent, an AI agent, to serve as sort of an expert analyst.
And this could be useful for someone who has perhaps less experience using the tool.
And, I've… I've worked on some other prototypes where that's the focus.
Where you're trying to capture what a particular analyst might be doing, And the idea is…
It does… it could do a lot of the work, perhaps, in terms of, like, adjusting parameters,
So in that case, just offloading what an individual user might do, or again, provide suggest… suggestions or clarification, so… but again, that would be icing on the cake.
Aidan Schlesinger
00:44:13
Okay, perfect, sounds great.
David Xiao
00:44:22
Alright, well, hope you guys don't mind, but I think I'll take up the rest of our time in that case.
So, okay, so in terms of big picture, the task we're currently working on is we kind of want, like, different UCTs for comparison, since, like, you know, let me,
Since, basically, we have a prediction that comes from the model.
let's say that… I'll call it P0, and then we have, like, the…
The actual answer, let's say that's, A0.
And for every different model, basically, there's, like, a difference between what they predict and then what they actually do, right? So, ideally, we have a good model.
And then we'll call this… let's say M…
M1, and then we have a…
Model that's, like, kind of mid, and then we have a model that's kind of bad.
So, basically, the idea is, like.
we… you need to, like, evaluate the scores, right? Say that this 90, you know, 80, 70…
We want to make sure, essentially, that our benchmark.
We want to make sure that our benchmark doesn't say that this is, like, a good model, for example, and then this will be a failure mode.
Basically, we need to, like… what we need is we need to have an accurate assessment of whether a model is good or bad.
If I understand correctly. So that's why we're currently looking for all of these models.
But I'm also wondering if, like, you know, we could just already use the UCT dummy processor as our bad model.
Louis Caves
00:45:58
Yeah, so the dummy… dummy UCTV is definitely going to be a bad model. It's not actually doing any sort of, orbital estimation or any kind of math at all. It's just…
Putting things in the proper format.
And then your question of what is a good model, what is a bad model, like, we need to make sure that, you know, bad models get rated bad, and good models get rated bad, good. You know, that is a…
potential way to calibrate your scale, right? Just take a whole bunch of different processors, one we know sucks, and set that, you know, calibration point to zero, and another one we know is phenomenal, and set that calibration point to 90.
Or, there's another way to calibrate, you know, our scale, which is to actually look at, the outputs, and instead of using a data association and say, like.
You know, this is…
Let's… let's use an example of a thermometer, right? You can calibrate a thermometer with, you know, ice water and boiling water. You put the… put the thermometer in the ice water, and you mark it. You put the thermometer in boiling water, and you mark it, and now you've got a scale between 0 and 100.
The other way to calibrate a thermometer is to say, okay, well, I know what the material inside of the thermometer is, I know what… how much volume I have, and I know, you know, how to calculate the rate of expansion due to changing temperature. And you calibrate your scale with
You know, physics, science, math, underlying, you know, engineering principles, such that you don't need those calibration points.
So the way that we're going to calibrate the pro-
Calibrate our scale is the fact that
what defines a good UCT processor? Well, a good UCT processor is going to…
you know, accurately estimate the orbits. So, we're going to calculate, based on our reference and the output, how far away are those orbits from each other. It's going to…
correctly associate all of the observations with the correct objects. So we're going to go through, and we're gonna make sure that all of those objects are correctly, associated.
And if the… if the states are off, you know, we lose… you lose points there on your processor. If your, you know, observations are incorrectly correlated, you lose points there. If your sum of residuals is really high, then you lose points there. So, we don't necessarily need to collect a whole bunch of different data points on a whole bunch of different processors and calibrate our score that way. We're going to calibrate our evaluator based
on… what does a UCT processor do by definition?
And how…
you know, by definition, a good processor does this, this, and this. And we selected our metrics such that they should be representative of
You know, a good processor doing well, and they should be representative of when a bad processor does poorly, it should be able to see that and reflect that in the final evaluation.
Now, the metrics that we have chosen aren't necessarily immutable, they're not all-encompassing. If we can think of other ones with a good engineering rationale of why they should be included, we, you know, not just should, but are, you know, necessarily required to include those. If
We go through our list of metrics, and we find, for some reason, with good engineering rationale, that
You know, this is not a good metric, because then we would be required to either de-weight or remove that metric, because we want our scale to be
as…
representative of the output as possible. And in order to do that, we don't necessarily need a bunch of different processors to test, we just need to know what the end result should be.
David Xiao
00:49:54
Yeah, so in that case, evaluation is kind of built into our current model, then. So, would you say that we currently need other UCC processors? Since, like, our team was thinking about creating our own, and I'm wondering, firstly, if that was a productive use of our time. So, like, I mean, now that, like, listening to the explanation, I'm wondering what your thoughts are, like, do you think that we should create one of our own, or should we focus our energies elsewhere?
Louis Caves
00:50:17
We'll probably focus our energies elsewhere.
When we first conceived this project, and we were working on it all summer, we were always acting under the impression that this UCT processor
or, you know, the space of UCT processors that we could feed this dataset into is and will remain to be a black box. We don't know how it works, we don't…
want to know how it works, it doesn't matter how it works for the functionality of our program. We're going to create a dataset that's reminiscent of real-world UCTs. We're going to take the output from Black Box Processor and compare that to the known reference.
Between the dataset creation and the evaluation of the output, that interior black box, we don't need to know.
David Xiao
00:51:08
Got it.
Louis Caves
00:51:09
Because it shouldn't matter how the UCT processor is built, as long as it's…
doing what you think it's doing, i.e. giving you a list of candidate outputs, then it doesn't matter how the UCT processor is doing it, it just matters that it did it, and now we're gonna say, how well did you do?
David Xiao
00:51:29
Yes, understood. Alright. Thank you, that's very helpful. So, I mean, from what I understand, then, that our team is probably gonna have to pivot to something different.
Although, I'm not really sure what we're gonna work on in that case, so… I mean, I think it's good that we have this conversation, though, since, like, it's probably good to just, like, kill the baby early, that way we don't invest too much into something that's probably not gonna pay off, but I'm thinking that I'll probably have to meet with the other team leads and then try to figure out something else for us to do, but thank you very much, this was very helpful.
Louis Caves
00:51:57
So I think… I think what would be good, what would be helpful for us at this point in time, is for if everyone, each one of your individual teams, could take whatever they're doing.
Put it into the simplest, you know, presentable format that you can.
And I don't want everyone to push that to the GitLab on your own respective branch is fine. I just want to be able to follow along with what you're doing. And then at our meeting next week, I'd like to see everyone go through and…
Present on, you know, what they've done and where they're at.
And based on…
where we are, we can get better alignment between all different teams and all of our different mentors, and figure out where we are, where we need to get to, and if we're, you know, out of alignment on anything, then we can have a discussion trying to bring things back together.
David Xiao
00:52:53
Understood.
Got it, thank you very much.
Yeah, I believe that that was most of what I have. I'll definitely have to talk to my team about that.
Evan
00:53:04
So, in terms of… I have another question, but I know we've kind of reached our time, so, like, if you have something to go to, Lewis, like, this can be something that we talk about, later.
Louis Caves
00:53:13
Oh, no, that's… that's fine, go ahead.
Evan
00:53:14
But… so in terms of the… evaluation criteria.
So it's based on what you were talking about earlier, it's my understanding that
We have a good idea of…
that the fact that these evaluation criteria that we already have set up are probably pretty good, but there's some flexibility there, we don't know for sure. Like, maybe there's other metrics that we want that are better, maybe some of them aren't that good, we want to drop them.
Maybe we need to calibrate some of the thresholds for them to determine what is good and what's not good.
Louis Caves
00:53:45
Right.
Evan
00:53:46
And to achieve that, in my mind, kind of what I'm thinking is that what's needed is
like, a good UCTP
output, so you can calibrate them, like, okay, this is good. And then, a bad UCTP output, obviously, to calibrate the bad.
And I guess maybe, like, a middling one to make sure that it hits, like, the middle scaling.
correctly is, like, a good evaluation gradient, I guess? Does that make sense to you?
Louis Caves
00:54:14
Yeah, I… I see… I see what you're going for. It's like, if you give… if you give someone a test that has 100 questions, and, you know, person A gets one right, Person B gets 2 right, well, Person B did twice as well as Person A, but…
On an absolute sense, they both failed horribly.
Evan
00:54:33
Yeah.
Louis Caves
00:54:34
Yes, I, I do, I do see your point.
Evan
00:54:43
And… I guess an issue with that is perhaps…
That a little bit sets the standard…
by… like, in the terms of modern UCT processors, such that, you know, if we just take a good one, and then we say this is their criteria for being a good one, I mean, that's great and all, but…
how do we know it's a good one? I mean, I think the whole point of this project was a little bit that there's no…
Great, like, standardized, universal…
Place that people can go to and say, this is what it means to be a good one, right?
Louis Caves
00:55:16
Exactly. So, when we say, run it on a good processor, what is good? So…
to what I was saying earlier about, you know, good is, by definition, you know, this, this, and this. So, how close to the true orbit is the actual orbit?
To quantify what is good, we can go…
even a step further than the UCT processing is when you process the UCT, UCTs, and you get this state vector.
what do you do with that state factor? Why do you want it?
Right? What… what are you… what are you planning to do with that state factor? Are you going to try and maintain custody of an object? Do you want to…
be able to say, like, how accurately can you propagate it forward until the next time you see it? So…
there is a threshold of what good is based on what you're gonna do with it, right? If you see this object every 20 seconds, and, you know, it's really hard to lose track of, your orbital estimate doesn't need to be spectacular, because you're gonna see it again in 20 seconds.
the 3 days.
you want to have a super good orbital estimate so that you can propagate that state vector for another 3 days, and then look for it again, and be like, hey, look, it's right there where I thought it was. So…
The threshold for what is quote-unquote good for that orbital estimate is determined by
implementation. How good is good enough? Like, if we look through and say, you know, this UCT processor, even if we had 3 different UCT processors, you know, or one is
it's significantly superior than another, even if we go through and say, oh, well, the RMSC of residuals on this one was 0.2, therefore 0.2 is our threshold for good.
Well, suppose that, you know, the application that we need that state vector for says that, you know, if your RMSE is anything above .05, it
doesn't help us at all. Well, now, all of a sudden, what we thought was good based on where we tested our UCTPs, is now actually not good. And all of those processors fail. Everything that got
you know, either one or two questions right, regardless of the fact that, you know, getting two right is 100% better than getting one right. If you needed to get at least 75% right to pass the class or whatever.
You know, they both still failed.
So, it's not necessarily a relative comparison of, you know, this one was twice as good as this one.
But it's more like an absolute comparison of, we need this auditable estimate to be at least this good in order to be used downstream in whatever they're using this UCT processor for.
Jon Cline
00:58:20
Okay, okay. This is a great conversation. I was just… just thinking, this is getting back to, having used, example UCT processors to work with. It would be useful, I… I… I'm not saying it's possible, to have…
sort of a representative set of UCT processors. I know it's a challenge just to get one, in the sense that it would be nice to have some subject matter expert say, oh.
here's my UCT processor, it's good at this, and then you just put a number on the table.
And at least there you have…
a set where you have some opinions about how they function.
Because, I mean, I don't… yeah, it's not up to… to… to this team to figure out what's good. I think where it becomes interesting is when…
I mean, again, if we could get some contributions of, hey, I'm volunteering my UCT processor, I think it does this.
That would be great.
And one of the reasons why I find this an interesting exercise is often what you have
In sort of this domain? You have… you have many different companies, you have different parts of government.
They may have, particularly in the for-profit side, you have a lot invested.
in these processors. So, and that is…
why you would want something like a UCT processor, because you don't necessarily want the folks who are
Are presenting the candidates to write the test.
Because otherwise, the temptation to write the test…
To, to fit your product is too tempting.
Evan
01:00:25
Sure. So we're… Kind of becoming a…
standardized test creator and proctor for these UCTP, or UCT processors, so we can give them the test, and then
they do the test, and we grade them on it and say, okay, you got these grades and all these different metrics and stuff. You can do with it whatever you'd like, decide what's good enough for you, what's not good enough for you, what measurements you care about. Like, we're the neutral third party.
Is that correct?
Jon Cline
01:00:51
Right, so that's… I mean, that would be helpful, and I'm also speaking from the perspective of this is…
this is a… one of the… one of the purposes of federally funded research and development centers is to provide sort of a neutral, or as… as neutral or objective testbed. So…
you may have the various stakeholders, they come to agreement about… it's like, okay, we're all sort of working on the same thing, can we agree on, sort of, some general parameters? And then you have
an independent party actually designed the tests.
I mean, I'm biased because that's… that's… I'm working in this space, so we're not necessarily going to build the models. We may build a model just to test it out.
But this is about designing the test, so I don't know how this would… will work out going forward, but it's definitely something that's needed.
Okay, I want to add another thing, is at this point, I'm sort of…
I may not be as available because we've had a hiccup in funding.
But I just want you all to know that I will still be available, and I will be following up as best I can.
David Xiao
01:02:17
Thank you very much.
Jon Cline
01:02:19
So…
Bryant Ortega
01:02:19
Thank you, Dr. Clinton, and I appreciate… we all appreciate, the guidance and all the help that you've provided for us, so…
Good luck.
Jon Cline
01:02:27
And this is particularly… this is particularly focused on the… on the… I'm…
We would like to be able to get, get the… the… this…
toolkit, on the federal AI sandbox. At the moment, it's just a question of figuring out who's going to pay for it.
David Xiao
01:02:52
Understood.
Jon Cline
01:02:53
So basically, we're gonna wait until funding shows up.
No, I… what I'm saying is continue doing what you're doing. I am going to try and monitor what you have as best I can. I do have access to the SuperPod, so to the extent
We may have an opportunity to,
Sort of, if you could evaluate… work with what you have.
then we may be able to make the case and say, hey, if we… if we could scale it up, if we had access to this level of processing, we think we could do better. So, at least…
You know, this gets back to, as long as you have a minimum viable product, that provides a better
Justification for further funding.
David Xiao
01:03:45
Got it.
So, work towards that.
Jon Cline
01:03:48
Yeah, so, yeah, we're… yeah, so this is not… yeah, this is… you're going in the… this is… this is a… I think it's a worthy project, otherwise I wouldn't be…
Doing this. So, and, so… Appreciate your work on this.
David Xiao
01:04:04
Of course.
I think that that would be most of my questions for today. Evan, you got anything else?
Evan
01:04:10
I'm… I mean, I guess… If we still have…
Time that you guys are, down to talk. Just chatting a bit more about the…
the work that needs to be further done in terms of this… these evaluation metrics and stuff, like, what should be our next steps on that? Is that our responsibility, or is that going to be something that y'all are taking care of and you want us to focus on other parts of it?
Louis Caves
01:04:42
As far as the evaluation, I think that the evaluation pipeline was left off in a pretty good spot. There are just a couple of…
small things.
that… Don't necessarily contribute to the main functionality.
there is a way for… to go through, you know, given dataset and output. It'll run through the orbit association, it'll calculate the state metrics, the binary metrics, the residual metrics, it'll package that all, and it'll give you a final output.
So I think the majority of our focus right now needs to be in finishing dataset generation pipeline. Once we can do that and go from
user input through the UI, or command line interface, or whatever our chosen method is, go from user input to, dataset in our database storage.
And then we can go back through and look at
using our UCT processors, either dummy processor, or if we choose to put together something else. Then we look at, you know, here's the data set using this dummy processor to convert this to output. We put in our data and output into the evaluation, then we can start looking at, well, this is how the evaluation, pipeline performed, given this set of
Reference and output.
But for now, we're finishing the dataset generation pipeline. We're making good progress on the UI, but we need to make sure that all of that same functionality is there outlined in documentation. We need to go from
user input through all the UDL queries to pull the observations and the necessary state factors. We need to go through the, time window and window selection and the tier scoring,
all of that should have been in a pretty good spot, and then what we need to do is we need to go from, you know, we've identified the optimal time window, we've identified, you know, whether we're, you know, Tier 1,
bound sampling, simulation, or, you know, object simulation is required. We need to go from there to figuring out
Whether we need to implement simulation, or downsampling, or both, and we need to figure out
How do we figure out which observations need to be simulated? How do we figure out which
Objects need to be simulated in order to get the specific…
data quality input parameters that the user selected. So, we need to go from…
you know, after we pull all the data from the UDL, then what? You know, how do we identify
Downsampling required, yes or no. Simulation required, yes or no. What… what objects do I need to simulate? How do I tell which objects do I need to simulate? Which objects need to be, downsampled? How do I know which objects need to be downsampled?
So, this is why I think it would be helpful to have everyone take what they're working on. We'll push it all to the GitLab, we'll be able to sit down and go through every piece of it and say, like, you know.
This works well, this works well, this works well. Right here, there's a gap in logic, we need to fill this in.
And then presupposing that works, then the next thing in the pipeline, this works well, this works well, and then there's another gap in logic here, this doesn't work well, we need to… and then we can, you know, help refine, like, if the pipeline was to be complete, we would need, you know, this to be looked at, we would need this to be looked at, and we need this to be looked at, and then we can kind of, like, refocus
Our efforts onto the specific, pieces that are, that are broken currently.
Evan
01:08:47
Sure. That makes a lot of sense. Yeah, it is really defining what the…
criteria are for the MVP, and making sure that we're hard-focusing on those, get the MVP done, just so that we have a working product.
Which will be helpful for funding, hopefully, as well. And then we can focus on the more, like, you know, second level, more fun stuff, maybe, or other interesting stuff.
Louis Caves
01:09:10
That's exactly right.
David Xiao
01:09:14
Yeah, and that said, Brian or Kelvin, since you guys are primarily on the MVP pipeline in that case, is there any tasks that you guys want to delegate to us? Since, like, since if we're not going to dedicate time to our UCT processor, I'm guessing that we are currently free to take out more tasks.
Bryant Ortega
01:09:29
Currently, just kind of looking at everything and seeing, what we are supposed to be focusing on. I think it'd be useful if your UCTP analysis team starts looking into.
like, the actual, like, dataset generation aspect of everything. So you guys, kind of have…
out of the entire team, I think your team probably has the most understanding of, sort of, like, what a UCTP processor does, that way you guys can start thinking of what sort of datasets are we generating, what kind of parameters do we want to include. Even if we just start thinking about it now, we could very quickly start, actually getting to that point where we're generating those datasets.
I know…
in terms of focuses for our teams, just to keep it very general, I wrote down, creating these datasets to actually test the UCT processors. Then eventually we'll have to… well, it sounds like the metrics are already kind of established for, evaluating these UCT processors.
So, if anything, just making sure everything's working well. If there's any metrics you guys would like to add, or anything that you guys deem we'd want to do, feel free to. And then, obviously, storing these datasets,
the database, the data storage team is working on that for you guys, so… Okay.
Evan
01:10:54
I know in the, in the benchmarking documentation.
document, there is a file I.O. format.
Section that details what I believe to be, like, the expected schema for the…
output for when you're generating datasets? Like, what.
Bryant Ortega
01:11:14
It should kind of look like.
Evan
01:11:16
Is that…
Is that pretty set in stone? Like, that's how it should look? Is there things that we should change?
Louis Caves
01:11:24
So, the, the dataset, each observation, this is the schema that
the observations are in… from the UDL. So, when we query our data from the UDL, this is the information that the UDL is giving… giving back to us in this… in this schema. We're not using all of this information, we're only using,
a few of these fields. We need the ID number, we need the op time, we need…
Some… somewhere we need the satellite number, we're gonna get rid of that eventually. Azimuth, elevation, range, RA, declination, send let, send long, send out.
and then, type optical. But everything else is really just, like, extra. We don't actually need it. So…
to… when we make our dataset, if we save all of the metadata for each observation that UDL gives us, it will probably become
unnecessarily massive, as opposed to if we chop out, certain columns. But we need to be smart about what columns it is that we're chopping out. We need to make sure that we're not
removing any information that a UCT processor might want. Because remember, the UCT processor is that black box in the middle. We don't know
if… a particular UCT processor might want zero PTD,
float value, whatever that… whatever that is. I don't know what it is, it's a… it's a value on the schema that UDL gave us. Maybe there's a processor that uses that information for something. So if we cut out that information, then the UCT processor all of a sudden doesn't have a piece of information that it deemed to be important.
So if there is, you know, any, you know, subset of these fields that can be eliminated that we absolutely will not need, don't contribute any value whatsoever, then, you know, we can… we can chop it down.
Yeah, we'd have to… we'd have to be smart about how we filtered for this data.
TLE dataset, we're not gonna worry about TLE datasets right now, UCT processor output.
That is…
based on the way we have defined our metrics, it is looking for fields in the output JSON structs that are
in this schema. It's looking for a field that's called IDStateVector. It's looking for a field that's called source data. It's looking for fields called Epic, XPOSS, Ypos, ZPOST. So…
whatever the UCT processor gives out, it could be more information than this. It can't be less information than this. If they give us… if they give us, you know, XPOS, Ypos, C++, but no velocity.
And we can't do anything with it. In order for our evaluation script to work, we need at least
this much information.
And it has to be in that right schema. If it chooses to call, you know, instead of XVEL, YVEL, ZVEL, it might say, like, VX, VYVZ.
Currently, that doesn't work for us. You know, it's going to be looking for a specific column in a pandas data frame called, you know, lowercase XVEL, and if it's not there, it's gonna throw an error and say, hey, this wasn't here. So…
That's something we can do to generalize once we build that minimum viable product to work with a very specific type of output, is we'll suppose, you know, the outputs are, you know.
called something slightly different. If it's a syntactical thing, add in some error checking to say, you know, VX and X velocity, or anything that looks kind of similar to that, you know, that's all the same information.
But for right now, the way that, you know, our value script has been defined, it's looking in the output truck that we give it for these values in particular, and if they're not there, it's going to give us an error.
Evan
01:15:46
Understood. That makes a lot of sense. Thank you.
I think that's all the questions that I…
have for now. Unfortunately, I do have to head out to class, but wonderful talking with you, Louis. I really appreciate all the information and making sure that we're on the right path to do the most relevant work.
Louis Caves
01:16:06
I appreciate the insightful questions.
Evan
01:16:09
And I'm excited to get some work done and then talk with you again next week.
Hopefully with some good updates.
Louis Caves
01:16:15
Thanks, Evan.
Evan
01:16:16
Alright, see y'all.
Bryant Ortega
01:16:17
Thank you, Evan.
Jon Cline
01:16:18
Right. Thank you.
David Xiao
01:16:26
Well, I believe that that was pretty much everything then, unless you got anything else, Brian? Or Colvin?
Bryant Ortega
01:16:31
No, personally, I don't have anything else. I do have some notes written down, just in terms of, like, really pushing, the areas that we need to focus on as a team.
So I think I personally greatly appreciated this, this conversation, this meeting, because it'll help us ultimately kind of realign and really make sure that we
We're, directing all of our energies towards, what we need to, so… Yeah.
David Xiao
01:16:57
And that makes sense, and I'll definitely want to see you guys next Tuesday, like, I'll probably hop into your guys' room, and then, like, I'll need to ask for, like, more specifics about the tasks that we need to do. But other than that, I think that we are on a good spot for today, so…
Bryant Ortega
01:17:10
Yeah, that was good.
Take it easy, David, you know how to reach me.
Louis Caves
01:17:17
So yeah, for next week, I'd really love to see, everything that we got pushed to the GitLab so I can follow along with you, and I'd really like to see
you know, it's okay if everything's in bits and pieces, it doesn't have to be, like, a full, you know, product demonstration, I just want to see, you know, where we're at currently, so we can, you know, get that… get that, better alignment on where we're going. So if we can have that ready for next week, that'd be great.
Bryant Ortega
01:17:45
While we're on the topic of GitLab, I was working with my team, because we wanted to take a look at Dr. Klein's, like, factored code, but our team is still waiting on SDA TapLab… on GitLab.
GitLab access, specifically. So they can get into their accounts, but we need that. Do you recommend just shooting a message into the infrastructure rocket chat?
Louis Caves
01:18:07
So, what is…
Well, firstly, yes, I… I… I would, I would say do that. But, like, what, what is the issue? So, they're… they're on… they're on Rocket Chat.
Bryant Ortega
01:18:20
They have Rocket Chat, they can log into the SDA Tap Lab, but they don't have the GitLab tile, because I believe Melissa hasn't…
Pushed access for us quite yet.
And then, once we all have access to GitLab, I feel like that would help, all of us push our progress if needed, because I think currently only the original students can…
access everything that's on GitLab and, Push. And the majority of the students, so, like, all the new students that, have joined us, they're working off of a,
a repo on GitHub that Kelvin has been hosting for us, if I'm not mistaken.
Louis Caves
01:19:01
Yeah, so…
for… if you… if you get on Rocket Chat, you go to… go to the infrastructure support channel and just say something about, GitLab access. I'm looking at the infrastructure
infrastructure support channel right now, and someone just asked about GitLab access at, 11.22 this morning, and…
Greg responded 3 minutes later, he's like, get lab added to your account. So, I think it's a very easy thing to do, someone's just gotta go through and click a button.
But yeah, you can just say, like, I need, you know, I need to get… get lab access. You know, you probably don't even need to say, you know, for this, that, the other thing. You can probably just say, I need… I need get lab access, but it wouldn't… it wouldn't hurt to say, you know, what you're…
what you're doing. Yeah.
And then remember the project in GitLab?
was, the, the group that you're a part of is marked as private, so…
when people are added to the GitLab, someone needs to specifically add them to the project, otherwise, they won't be able to… won't be able to see it. Remember, that was the issue that Dr. Klein and I were having. Right. When we… we couldn't see the new branch, because it was.
Bryant Ortega
01:20:25
Private.
Louis Caves
01:20:27
So…
I'm not sure who… who is the owner of that group, if you can change that to public, or if you want to just add, you know, members as they join GitLab, either way is fine. I… I don't…
I don't think there's any good reason why this project shouldn't be made.
Public, and when I say public, it's public for, the TapLab GitLab. It's our own private instance of GitLab, so public within the GitLabs, or within the Tap Labs GitLabs, so anyone
who's on the TapLab GitLab would be able to see it, but it's not open to, you know, just anyone who goes to GitLab.com, the same way that, like, a GitHub would be.
Bryant Ortega
01:21:14
Right. Okay. Yeah, we'll, go ahead and look into that. I believe it is Kelvin's code, so if, we could work on getting that changed.
We'll look into that.
Because I assume it'll just be easier to have it public. And how you said there's no reason it should be private.
Louis Caves
01:21:31
Yeah, probably, and then when it comes time to, you know, share our code with, you know, the higher-ups, or if we want to migrate over to what Dr. Klein was talking about SuperPod, or either when there's turnover in the project and we get new people coming or going, you know, at some point, whoever the owner of that project is is probably going to lead this project, and if that's
You know, if the project just gets locked behind a private group that a leader is no longer, you know, part of the lab, that could cause issues downstream.
Bryant Ortega
01:22:05
Right.
Definitely. Yeah, we'll work on that then.
Okay, and then, yeah, I guess that's all I really had then. I'll make sure to let Melissa know I sent a message in the infrastructure chat, because she…
Was planning anything, but…
Yeah, I'll, make sure that the students are working on some sort of, like, demo, whether this is, like, slides or some sort of, like, actual demo, just to update us on what we're all doing and kind of what we're focusing on.
Louis Caves
01:22:37
Yeah, if it is slides, I mean, slides are great, you know, it's… a lot of this code, it's big and it takes a while to run, so I don't think there'd be much to gain by staring at, you know, someone's VS Code terminal, watching it, you know, do nothing until all of a sudden there's an output. But…
you know, if we're gonna go over slides that says, you know, this code does this, this code does this, I would say make sure you run that code offline, and you can verify that, you know, this
does actually do this thing that we're claiming it to do, give, like, a sample of, you know, this is the input that we gave into the function, this is the output that came out of this function, this is what we'd expect, and this is why
We'd expect it, because the next element in the pipeline requires, you know, this specific output of this function as the input to the next thing.
Bryant Ortega
01:23:33
Okay. Sounds good, y'all. Make sure to have everybody do that then.
I know…
like, a pre-recorded demo. I'll tell everybody either a pre-recorded demo or how you said slides with, like, samples of inputs and outputs.
Louis Caves
01:23:48
Yeah, and like I said, it doesn't have to be anything crazy, you know, it's not… it's not a test or anything, I just… I just want to see… see where we're all at, and it'd be helpful for, you know, all of our different groups to come together and see where everyone else is at as well.
Bryant Ortega
01:24:04
Yeah, I completely agree.
Alright. David, Kevin, do you guys have anything to add?
David Xiao
01:24:12
No, I believe that that was all. So, I mean…
I think I'll be heading out in that case.
But again, thank you, you guys, all of you, for your time here, and really appreciate you answering all the questions, Louis.
Louis Caves
01:24:24
Alright, yep, thanks everyone, I'll see you guys next week.
Bryant Ortega
01:24:27
I'll see you next week.
Thank you, Luz.
Kelvin Benedict
01:24:34
Nice.
Bryant Ortega
01:24:34
Right. That was, that was a good… Good meeting.
Kelvin Benedict
01:24:38
Yeah, that was.
Bryant Ortega
01:24:40
Yeah, I'm happy that we got that recorded. I took a couple notes,
I had a feeling that we might be flying a little too close to the sun with the UCTP processor, the processor, but, you know, it's… it never hurts to try, right?
Kelvin Benedict
01:24:58
I also think we're probably a little closer,
for the data ingestion part than most people think. I mean, I think we got basically everything built.
Bryant Ortega
01:25:09
Yeah, so it really just is, I guess, like, ironing out the wrinkles, is what it seems like, and then, it really sounds like…
Cause I have a couple things written down. Oh…
sent him into the chat, actually.
Because just from Louis' conversation, this is kind of what I got in terms of, like, what our team should focus on.
And I'll share my screen. But it does kind of sound like he is mostly concerned with,
finishing that data ingestion, which is, you know, simulation, downsampling, and everything,
And… well, yeah, it seems like we're getting really close on that with everybody that's on your team. Yeah.
And then additionally, I also have,
Well, I guess the main focus, which is just…
actually establishing these, datasets that we're gonna be using to evaluate the UCT processors. So, it seems like we're soon gonna be able to focus on the actual, like, datasets, and establishing the metrics, and then actually storing the datasets.
But, yeah, what do you think, specifically looking?
Overshooting.
Kelvin Benedict
01:26:25
Yeah, I mean, I think… I mean, it's, like, really legitimate to focus on the dataset generation, because that's, like, step one of the pipeline. If that doesn't work, the rest of it's kind of useless.
Bryant Ortega
01:26:33
Right.
Kelvin Benedict
01:26:35
But, I mean, I kind of think we should do it, like, through the UI. I mean, it seems like that's going to be the way that most people are gonna use it, that's kind of their vision, so I think we should probably focus on the UI.
But, I mean, man, I really think we're just in good shape. I think, like, I could probably steal someone.
from David's team, or even just part-time, still someone from David's team to help out Tara with downsampling.
Bryant Ortega
01:27:00
Is Kara the only one that's working on downsampling?
Kelvin Benedict
01:27:03
Yeah.
Bryant Ortega
01:27:04
Okay. I definitely think, cause also after our conversation today, it does seem like the, UCTP team is kinda…
in shambles a little bit. I could see it in David's face, he was like, what do we do now? So, yeah, I think definitely giving them the opportunity to hop on the dance sampling team, whether it's, like, one or, you know, just a few students on there.
Kelvin Benedict
01:27:28
Totally. Because it's James and Patrick is on, simulation, so I'm not… I'm not worried about that. Both of them are, you know, real studious and motivated and technical, so I'm not worried about that. I think mostly, yeah, downsampling, and then…
Yeah, I don't know, it kind of sounded like Lewis wanted to wait until we had, like, MVP working before we implemented other data sources, so…
Bryant Ortega
01:27:53
Yeah, and I kind of, I kind of agree with Lewis, just because I feel like if we get MVP working with just the UDL, I don't think it'll be hard to get it working with everything else, especially if we set it up in a way where it's kind of like plug-and-play, like, oh, now we want to pull in from this.
And then we know exactly where we have to, like, throw everything into, you know?
Kelvin Benedict
01:28:14
100%.
Bryant Ortega
01:28:15
Yeah, so I guess, big things too, and I might try working on this myself, too, as well, is just, really establishing…
Identifying… and focusing on MVP. So,
Yeah, I think I'll try to work on that, kinda.
get everybody on the same page, at least. Cause then also, when it comes to the UI team, what…
Because it kind of…
I don't know, I think I still like having the UI team as, like, a sandbox, because I feel like they produce a lot of, like, good ideas and whatnot. You know, but maybe we could get them working on MVP. What I was thinking was, and this is just me spitballing,
We could have…
kind of how, AI is kind of established right now. You know how there's the terminal version, and then there's, like, the IDE version?
Kelvin Benedict
01:29:14
Yeah. You could very much have, like, a UI version and a terminal version as well.
Bryant Ortega
01:29:19
Where, like.
Kelvin Benedict
01:29:19
Yeah, I mean, I've tested… I've tested on both methods, and it works for…
for my code, at least, either through Terminal or through the UI.
Bryant Ortega
01:29:30
Oh, okay, so in your code, it's set up, so that you could run it through the terminal as well?
Kelvin Benedict
01:29:35
Yeah.
Bryant Ortega
01:29:36
Awesome. Yeah.
Kelvin Benedict
01:29:37
There are, like, yeah, there's, like, scripts you can run, and, like… I mean, that's how I do, like, a lot of testing, is I'll just tell Claude, like, hey, like, pull, you know, just… don't even use the UI, just, like, pull, generate a dataset, make sure there's actually observations, and make sure it works.
Bryant Ortega
01:29:51
Yeah, that's awesome. Hell yeah. Then I think we're in good shape, I think,
really, it'll just be… get this MVP pushed out, get it, like, in a good spot, as close to finished as we can, and then we can also have a good chunk of our team looking into, like, the actual datasets and the metrics.
Kelvin Benedict
01:30:13
Yeah, I agree about that.
Bryant Ortega
01:30:15
Yeah, so…
Kelvin Benedict
01:30:17
I mean, it's almost like we could steal…
I don't know, like, Noah or, or Aiden off the…
UI team and put them on something more MVP-focused, too, because, like, UI team and, like, David's team are kind of just, like, you know, past MVP, which is not a bad thing, but it's also, like, maybe we should focus a little more on MVP before we focus on extra.
Bryant Ortega
01:30:41
I think, yeah, and I know… I personally, I didn't mind, like, getting those teams up and running, because the way I see it, fail fast, fail big, and learn fast. You know what I mean?
Kelvin Benedict
01:30:55
Yup.
Bryant Ortega
01:30:55
I feel like, really, there's no harm in
you have an idea, okay, let's look into it, let's research, let's see if it's viable. And this… today was a perfect example. Whether we flew a little too close to the sun with wanting to build our own processor, while it would have been impressive, we ended up learning very quickly that might not be very viable, and also it might not be too necessary for our project. So now we know we have all this energy that we can start
Redirecting elsewhere, but…
Kelvin Benedict
01:31:25
I agree.
Bryant Ortega
01:31:26
Yeah, so,
Well, what do you think in terms of, I guess, where the project stands? So, definitely pull in some people from the analysis and the UI team towards ingestion and downsampling?
Kelvin Benedict
01:31:41
I mean, yeah, I mean, I kind of think we should just, talk to the teams on Tuesday and be like, hey, like, we're looking for, like, maybe one person from…
a UCTP analysis team, and then one person from UI team to switch over and focus on… I mean, it sounds like data ingestion is most of it, but maybe data storage if you need more help, but just to focus more on the MVP stuff, and… because I'd rather the students pick, like, I don't want to be, you know…
Bryant Ortega
01:32:07
Anybody, yeah.
Kelvin Benedict
01:32:08
Yeah…
Bryant Ortega
01:32:09
No, I completely agree with you, so,
Yeah, I think data storage, well, it is 3 students currently, I feel like if we take one more on, maybe 2 more, it wouldn't be, like, terrible.
But yeah, we can… I definitely agree, we should touch base. I think I'll try to prepare something,
maybe if I can come up with some sort of, like, Gantt chart or something to more, like, specifically say, this is what we should focus on. Like, these are the… more specifically, like, the tasks that we should really get out of the way.
Kelvin Benedict
01:32:43
Totally.
Bryant Ortega
01:32:44
Yeah, I think I'll focus my energy on there as well, so…
Kelvin Benedict
01:32:48
Yeah, I mean, that sounds great, and I'm also, like, definitely down to talk to, like, Noah or Aiden, so… Yeah. In person, and just be like, hey, like, y'all are doing great work, but, like, we just need to focus a little more on MVP, so would one of you be willing to move over to, you know, me or Brian's team?
Bryant Ortega
01:33:04
Yeah, yeah, for sure, if you wanna go ahead and, talk to them in person, maybe get them thinking about that a little bit, feel free to, but…
Yeah. Yeah. Honestly, I'm, I'm glad… I'll… I'll stop recording, actually. I forgot, I'm still recording. I'm glad.