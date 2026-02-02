Principles:

1. this is a repo for automated podcast production
2. we should organize the codebase this way: 
./output for all the generated output content. They should NOT be in git.
./src for all the python code. They should be in git.
./scripts for all the .sh files. We should always run the .sh files which uses venv and install from requirements.txt They should be in git.
./documents for all the docs. They should be in git.
./resources for all the input resources. They should be in git.
./experiments for ramdon things. They should NOT be in git.
./credentials for youtube secrets. They should NOT be in git.
./.env.secrets for API keys.  They should NOT be in git.

3. scripts/audiobook_pipeline_auto.sh should be the focus of this code base; it should create .venv and install deps before calling audiobook_pipeline_auto.py


4. all the py code should be moved to ./src with proper structures and imports
5. all the building block functions such as generating an image, generating a video or generating a json from LLM should be a function that is importable by other scripts and a standone script that can be run indivudually for quick tests;
6. we should AGGRESSIVELY resuse existing code;
7. scripts/upload_next_episode.sh runs as a cron job and uploads ALL pending videos:
    - Scans ~/upload_queue_main/*/metadata.json for videos with uploaded: false
    - Uploads each as private with scheduled publishing (publishAt)
    - Scheduling: find latest publish_at from all metadata.json, then add 24h for each new video
    - If no publish_at exists, start with 2pm NY time the next day
    - After upload, saves publish_at to the video's metadata.json
    - Result: videos go public one per day, 24 hours apart

8. we want to create a pipeline that create explanatory videos on hot topics; here are the proposed steps: a. use xai or perplexity to search for the latest news. b. use a good model from openrouter to pick one topic (as an example we can pick the geo/econ/political importance of hormuz when iran becomes a hot topic; or the history of nuclear development in China); c. use perplexity again to search related knowledge about it, then we write a script with a list of scenes -- each scene should have a narration and a scene_image_discreption, scene_image_discreption will be used to generate images, each scene should be about 15 to 30 secs; so narration should match that length; d. then we generate the audio using eleven labs. e. then we generate an image using open ai (here we should make sure that the image is not ultra realistic but illustrative purposes only); f. the image should be the background of the video with the audio from the same scene; g. eventually we should have a short explanatory video from 5 to 10 mins in total;   

