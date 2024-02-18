# Resume Optimizer
![](resume.png)

*Go the extra mile, without wasting thousands of hours. Achieve job market freedom using open source AI.*

An optimizer that takes a job description, a bank of experiences, and tailors your resume to the job description using AI. Check out an example pdf generated right [here](Ansh_Chaurasia_CV.pdf).




## Features
- OpenAI compatible -- uses OpenAI's GPT models, but the backend can be swapped out
for an open source model with a couple minutes of effort.

## Installation
The installation is designed to be fast and easy, via `pip`.

```
pip install requirements.txt
```

## Setup

#### Step 1: Environment 

Visit openai's website, and obtain an API key. Then, create an env file with the following content:
```bash
OPENAI_API_KEY="YOUR_API_KEY_HERE"
JOB_DESCRIPTION_FILEPATH="JOB_DESCRIPTION.txt"
``` 

*What is an open source, OpenAI backend model?*
OpenAI's API has become a standard in the LLM world for scalably 
serving large language models. As OpenAI has grown, developers have created projects like [localai](asdfasfdhttps://github.com/mudler/LocalAI), enabling users to "mimic" OpenAI's API functionality, while using open source models.

**Open source, OpenAI models setup**: Add an extra line to your `.env` file. The entire file is shown below, for convenience.

```bash
OPENAI_API_KEY="YOUR_API_KEY_HERE"
JOB_DESCRIPTION_FILEPATH="JOB_DESCRIPTION.txt"
OPENAI_CUSTOM_API="http://localhost:8080/v1/"
``` 
In this example, we assume that we use the v1 version of OpenAI's API, and that we are locally running it at port 8080 (works without change if you are using localai)

#### Step 2: Resume information
Edit `experiences.json` with your information.

That's it!

## Running the Program

#### Step 1: Loading the job description
Copy over your job description into `JOB_DESCRIPTION.txt`. If `JOB_DESCRIPTION_FILEPATH` isn't set in `.env`, make sure to point that variable to the filepath of `JOB_DESCRIPTION.txt`

#### Step 2: Running the Program
Run the program with `python main.py`. You will see the `output` folder become populated with various file, and a single `.pdf` file containing your resume.


### Miscellaneous
Added a `Makefile` for misc operations, like cleanup. To clean up old files, run `make clean`.

## TODO:

1. Add additional support, create more documented pathways for running the entire workflow open source!
2. Add in support for researching, and gathering relevant context / attempting to reasonably infer info about what the company may be delving into to provide extra tailoring information.

## Future
1. Support for LinkedIn / Gmail outreach with resumes