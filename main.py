import os
import re
import shutil
import json

from dotenv import load_dotenv
from utils.LLM import OpenAIChatAPI, OpenAIBackendAPI, LLMAPI
from utils.general import sanitize_for_latex, load_prompt_string, load_string, parse_json_garbage

from personal.experimental import generate_artificial_supplement_experiences


def generate_resume(info: dict, job_description: str):

    out = {}

    # Build the contacts section
    contact_info = info["contact"]
    out["cv"] = contact_info

    cv_out = out["cv"]
    # Build the education section
    education = info["education"]
    for e in education:
        e["highlights"] = [','.join(e["relevant_coursework"])]
    cv_out["education"] = education

    # Build the work experiences section
    work_experience = info["work_experiences"]
    cv_out["work_experience"] = work_experience

    # Build the personal projects section
    if "project_experiences" in info:
        personal_projects = info["project_experiences"]
        cv_out["personal_projects"] = personal_projects

    # TODO - smaller item: add certifications
    if "certificates" in info:
        certificates = info["certificates"]
        cv_out["certificates"] = certificates

    if "publications" in info:
        publications = info["publications"]
        cv_out["publications"] = publications

    if "custom_sections" in info:
        custom_sections = info["custom_sections"]
        cv_out["custom_sections"] = custom_sections

    # Build the skills section
    cv_out["skills"] = info["skills"]

    # Build the summary
    cv_out["summary"] = info["summary"]

    with open("resume_int.json", 'w') as f:
        json.dump(out, f)

    # Call the general command to render the RESUME in latex
    os.system('rendercv render resume_int.json')


def get_resume_in_text(info_dct):
    edup = load_prompt_string('prompts/utils/display/education.prompt')
    projectp = load_prompt_string('prompts/utils/display/project.prompt')
    resumep = load_prompt_string('prompts/utils/display/resume.prompt')
    workp = load_prompt_string('prompts/utils/display/work.prompt')

    edus = '\n\n'.join([edup.format(
        degree_type=edu["study_type"],
        university_name=edu["institution"],
        grad_year=f'{edu["start_date"]} - {edu["end_date"]}',
        coursework=", ".join(edu["relevant_coursework"])
    ) for edu in info_dct["education"]])

    works = '\n\n'.join([workp.format(
        company=work["company"],
        role=work["position"],
        time=f'{work["start_date"]} - {work["end_date"]}',
        experience=work["description"],
        location=work["location"],
    ) for work in info_dct["work_experiences"]])

    projects = '\n\n'.join([projectp.format(
        title=proj["name"],
        date=proj["date"],
        experience=proj["description"],
    ) for proj in info_dct["project_experiences"]])

    return resumep.format(
        education=edus,
        works=works,
        projects=projects,
        summary=info_dct.get("summary", "No summary provided.")
    )


def resume_text_optimize(company_name, job_description, resume_string, llm: LLMAPI, ITERATIONS=2):

    start_prompt = """
        Act as the hiring manager for this job. The company is {company_name} 

        {job_description}

        Here is my resume:

        {resume_string}

    """

    company_research_prompt = """Think deeply and clearly about the company, and list out your thoughts. Who is this company, in depth? What are their core values? 
    
    Then, go into deeper detail about the use cases the company provides solutions for. Step by step, think about what they would be doing internally that might require this job, or what other customers might be wanting the company to do. Finally, think about why the company might be hiring for this job. You will need to keep all 
    of this in mind for future conversations.
    """

    continue_prompt = """As the hiring manager, do you think that you can improve this resume's work experiences and project experiences substantially more to tailor it closer to the company knowledge you found early, and what they may seek through the job description? It's okay if not. I'd prefer you to start with a hard Yes or No. If Yes, list all the feedback you have. That means, that for any description, focus on concisely highlighting the most relevant results first, and then crafting it in a concise manner that highlights impact and displays skills that would be relevant to the job. Make sure to include impact statements with clear, quantiative results. Remember that a resume can be improved if the content in the resume can be adjusted to more closely focus on the task the job description focuses on, or if the description is too high level or does not contain clear action statements with quantative statistics in support. That would mean to remove / streamline irrelevant skills, and concisely elaborate on the more relevant ones"""

    implementation_prompt = """Now, show us how you would improve the resume. Rewrite the resume, and make sure to implement all feedback you proposed for the resume descriptions. Now, whenever we refer to resume in future conversations, we are referring to the latest refined version."""

    work_json_prompt = load_prompt_string('prompts/json/work.prompt')
    project_json_prompt = load_prompt_string('prompts/json/project.prompt')
    skills_json_prompt = load_prompt_string('prompts/json/skills.prompt')
    summary_json_prompt = load_prompt_string('prompts/json/summary.prompt')

    # Refinement loop
    p = start_prompt.format(
        company_name=company_name,
        job_description=job_description, resume_string=resume_string.strip()).strip()

    llm.prompt_and_response(p)

    resp = llm.prompt_and_response(company_research_prompt)
    print("Company Research: ")
    with open("company_research.txt", "w") as f:
        print(resp, file=f)

    # Squeeze in some details about the company

    # Iterate until we're done
    for i in range(ITERATIONS):
        continue_response = llm.prompt_and_response(continue_prompt)

        print("\n\n")
        print(continue_response)

        # We'll hard prune yesses
        if not continue_response.startswith("Yes"):
            break

        # If yes, implement the feedback.
        refined_resume_response = llm.prompt_and_response(
            implementation_prompt)

        print("REFINED")
        print(refined_resume_response)
        print("\n\n")

    # Post processing
    generate_artificial_supplement_experiences(refined_resume_response, llm)

    # Turn the optimized work section into JSON
    resp = llm.prompt_and_response(work_json_prompt)

    # TODO: bake in some more general skills to even out the resume
    print(resp)

    work_json = parse_json_garbage(resp)
    work_json = work_json["works"]

    for w in work_json:
        w["highlights"] = [sanitize_for_latex(o) for o in w["highlights"]]

    # Convert the project section into JSON
    resp = llm.prompt_and_response(project_json_prompt)
    project_json = parse_json_garbage(resp)

    project_json = project_json["projects"]

    for p in project_json:
        p["highlights"] = [sanitize_for_latex(o) for o in p["highlights"]]

    # Convert skills into JSON
    resp = llm.prompt_and_response(skills_json_prompt)
    skills_json = parse_json_garbage(resp)

    skills_json = [{"name": s['topic'], "details": ', '.join(s['name'])}
                   for s in skills_json["skills"]]

    # Convert summary
    resp = sanitize_for_latex(llm.prompt_and_response(summary_json_prompt).replace(
        "\n", "").strip())

    print(resp)

    return {"works": work_json, "projects": project_json, "skills": skills_json, "summary": resp}


# LOAD IN ENVIRONMENT VARIABLES
load_dotenv()

# ----- BEGIN USER PARAMETERS -----

# Switch to OpenAIChatAPI() if you want to use the experimental chat API -- note that none of your strings can contain this character: -> " <- .
llm = OpenAIBackendAPI()

# USER: CHANGE THE JOB NAME FOR MORE SPECIFIC RESEARCH / BETTER RESULES
COMPANY_NAME = os.getenv("JOB_COMPANY_NAME")
JOB_DESCRIPTION = load_string(os.getenv("JOB_DESCRIPTION_FILEPATH"))

DEFAULT_DESCRIPTION = "REPLACE THESE WORDS WITH THE TEXT OF YOUR JOB DESCRIPTION"
assert JOB_DESCRIPTION != DEFAULT_DESCRIPTION, "Only finding the default description! Copy in the actual job's description to that file!    "

# Work experiences pipeline
with open('experiences.json', 'r') as f:
    info_dct = json.load(f)

# ----- END USER PARAMETERS -----

# Processing
resume_string = get_resume_in_text(info_dct)


optimized_sections = resume_text_optimize(
    COMPANY_NAME, JOB_DESCRIPTION, resume_string, llm)

# Post generation
info_dct["work_experiences"] = optimized_sections["works"]
info_dct["project_experiences"] = optimized_sections["projects"]

try:
    info_dct["skills"] = optimized_sections["skills"]
except:
    print(optimized_sections)

info_dct["summary"] = optimized_sections["summary"]

if os.path.exists('test'):
    shutil.rmtree("test")


with open('experiences2.json', 'w') as f:
    json.dump(info_dct, f)

print("Generating resume", JOB_DESCRIPTION)
generate_resume(info_dct, JOB_DESCRIPTION)
print("Done.")

llm.quit()
