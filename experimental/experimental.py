from datetime import datetime


def generate_artificial_supplement_experiences(resume_text_string, llm):
    """
        Sequence of prompts to generate fake experiences that are reasonably
        doable in short time, but also capture the core essence of the job. Ideally,
        this would be a project experience.    
    """

    fakes_prompt = """
        Closely examine the job description I previously provided you with. Think clearly, step-by-step, and 
        verbosely, and be as critical as you can in your response. The job description layed out some requirements, and
        the candidate must have missed a couple technical parts. 

        What things has the candidate not included in his resume that could potentially make them a 10x better candidate?
    """

    llm.prompt_and_response(fakes_prompt)

    job_search_prompt = """
        Now, think deeply about the candidate's shortcomings. Again, think as slowly in steps as you possibly can. Given what you can see about the candidate's
        current experience level, what would be some reasonable and absolutely job-relevant projects the candidate could do to cover the shortcomings you mentioned above? List out a couple.
    """

    llm.prompt_and_response(job_search_prompt)

    imagination_prompt = f"""Now, imagine that the candidate did actually do the project you mentioned, in exactly the way you mentioned. Write the entire resume with the new project included in the projects section. Ensure that the new project's description on the resume uses some action statements with reasonably good numerical results that directly and precisely target the job description, and clearly quantify measurable points of impact that would demonstrate strong merit to the technical team. Set any dates to a time 1 month before today's date - {datetime.today().strftime('%Y-%m')} in YYYY-MM format. Make sure to add this project under the section for Projects and not for work experience. Don't replace existing project experiences, but add your new experience above them as the most recent."""

    llm.prompt_and_response(imagination_prompt)
