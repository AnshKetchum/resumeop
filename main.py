import shutil
import os
import json
import re

from langchain.vectorstores.qdrant import Qdrant
from langchain.chat_models.openai import ChatOpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
import openai

from dotenv import load_dotenv

from LLM import OpenAIChatAPI, OpenAIBackendAPI

load_dotenv()


# Configure backend if we want to go local
MODEL = os.getenv('OPENAI_MODEL', "gpt-3.5-turbo-1106")
if os.getenv('OPENAI_CUSTOM_API'):
    openai.base_url = os.getenv('OPENAI_CUSTOM_API')

llm = ChatOpenAI(temperature=0.7, model=MODEL)


def split_numbered_list(input_string):
    # Define the regex pattern for matching numbered list items
    pattern = re.compile(r'\d+\.\s+([^\n]+)')

    # Find all matches in the input string
    matches = pattern.findall(input_string)

    return matches


def load_job(job_name, job_desc_dir='job-descriptions'):
    with open(os.path.join(job_desc_dir, 'human', job_name), 'r') as f:
        job = f.read().strip()

    return job


def load_string(fp):
    with open(fp, 'r') as f:
        job = f.read().strip()

    return job


def load_prompt_string(file_path):
    with open(file_path, 'r') as f:
        data = f.read()

    return data


def get_impact(company_title, job_title, job_experience, job_description, n=2):
    prompt_impact_preprocessing = load_prompt_string(
        'prompts/work/impact_preprocessing.prompt')
    prompt_impact = load_prompt_string(
        'prompts/work/impact_quantitative.prompt')

    preprocesing_response = llm.invoke(prompt_impact_preprocessing.format(
        job_description=job_description, resume_experience=job_experience))

    print("Impact pre-processing", preprocesing_response)

    answer = llm.invoke(prompt_impact.format(description=job_description, company_title=company_title,
                                             job_title=job_title, candidate_bullet_points=preprocesing_response, n=n)).content

    out = split_numbered_list(answer)

    print(out)

    return out


def get_keywords(company_title, job_title, job_description, job_experience, n=5):
    prompt = load_prompt_string('prompts/work/keywords.prompt')

    answer = llm.invoke(prompt.format(company_title=company_title,
                                      job_title=job_title, job_experience=job_experience,
                                      job_description=job_description,
                                      n=n))

    c = split_numbered_list(answer.content)

    print("KEYWORDSSSSS", c)
    return [x.strip() for x in c]


def get_short_resume_description(company_title, job_title, job_experience, keywords, impact, job_description):
    prompt = load_prompt_string('prompts/work/short_resume_description.prompt')

    answer = llm.invoke(prompt.format(company_title=company_title,
                                      job_title=job_title, job_experience=job_experience,
                                      impact=','.join(impact),
                                      keywords=','.join(keywords),
                                      description=job_description))

    print(answer)
    return answer.content


def get_relevant_results(text: str, qd: Qdrant, score_threshold=0.6, k=3):
    retriever = qd.as_retriever(
        search_type="mmr", search_kwargs={"score_threshold": score_threshold, "k": k}
    )

    r = retriever.get_relevant_documents(text)
    for i, out in enumerate(r):
        print(i, "Experience: ", out.page_content)

    return [out.page_content for out in r]


def process_skill_description(info_dct, job_description, k=5):
    print("Processing skills! ", job_description)
    prompt = load_prompt_string('prompts/general/skills.prompt')
    out = {}

    # Gather all the keywords

    print("Grabbing keywords")

    keywords = []
    for experience in info_dct["work_experiences"]:
        keywords.extend(experience["keywords"])

    # Remove duplicate keywords
    keywords = list(set(keywords))

    print(keywords)

    print("Injesting data")
    qd = injest_data(keywords, collection_name="keywords")

    relevant_keywords = []
    search_thresh = 0.6

    # Lower the barrier to obtaining good results
    while len(relevant_keywords) < k and search_thresh >= 0.2:
        relevant_keywords = get_relevant_results(
            job_description, qd, score_threshold=search_thresh, k=k)
        search_thresh -= 0.05

        print("Thresh lowered to ", search_thresh, len(relevant_keywords))

    del qd
    print("Relevant keywords", relevant_keywords, len(relevant_keywords))

    # Run LLM to format the keywords
    answer = split_numbered_list(llm.invoke(prompt.format(
        candidate_keywords=','.join(relevant_keywords))).content)

    print('Keyword topic construction', answer)
    answer = [o.strip() for o in answer]

    for s in answer:
        print(s)
        try:
            topic, keywords = s.split(':')
            out[topic] = keywords
        except:
            pass

    return [{"name": o.strip(),  "details": out[o].strip()} for o in out]


def select_work(info, job_description, k=3):

    prompt = load_prompt_string('prompts/general/job_injestion.prompt')

    work_exps = []
    for experience in info["work_experiences"]:
        work_string = prompt.format(
            title=experience["position"], company=experience["company"], job_experience=experience["description"])

        work_exps.append(work_string)

    relevant_exps = []

    score_thresh = 0.65
    while len(relevant_exps) < k:
        qd = injest_data(work_exps, collection_name='work_experiences')
        relevant_exps = get_relevant_results(
            job_description, qd, score_threshold=score_thresh, k=k)

        score_thresh -= 0.05

    del qd
    # Use the selected experiences to match the actual chosen work experiences
    out = []

    for exp in relevant_exps:
        for experience in info["work_experiences"]:
            if experience["position"] in exp and experience["company"] in exp and experience["description"] in exp:
                out.append(experience)
                break

    print("Chosen relevant experiences", out)
    info_dct["work_experiences"] = out
    return info_dct


def select_by_relevance(info, job_description, info_attr, prompt_path, format_prompt, score_thresh=0.65, k=3):

    prompt = load_prompt_string(prompt_path)

    work_exps = []
    for experience in info[info_attr]:
        work_string = format_prompt(prompt, experience)

        # prompt.format(
        #    name=experience["name"], experience='\n'.join(experience["highlights"]))

        work_exps.append(work_string)

    relevant_exps = []

    while len(relevant_exps) < k:
        qd = injest_data(work_exps, collection_name=info_attr)
        relevant_exps = get_relevant_results(
            job_description, qd, score_threshold=score_thresh, k=k)
        score_thresh -= 0.05

    # Use the selected experiences to match the actual chosen work experiences
    out = []

    for exp in relevant_exps:
        for experience in info[info_attr]:
            if format_prompt(prompt, experience) == exp:
                out.append(experience)
                break

    print("\n\n\n")
    print("Chosen relevant ", info_attr, out)
    print("\n\n\n")
    info_dct[info_attr] = out
    return info_dct


def select_projects(info, job_description, k=3):

    prompt = load_prompt_string('prompts/general/project_injestion.prompt')

    work_exps = []
    for experience in info["project_experiences"]:
        work_string = prompt.format(
            name=experience["name"], experience='\n'.join(experience["highlights"]))

        work_exps.append(work_string)

    relevant_exps = []

    score_thresh = 0.65
    while len(relevant_exps) < k:
        qd = injest_data(work_exps, collection_name='project_experiences')
        relevant_exps = get_relevant_results(
            job_description, qd, score_threshold=score_thresh, k=k)
        score_thresh -= 0.05

    # Use the selected experiences to match the actual chosen work experiences
    out = []

    for exp in relevant_exps:
        for experience in info["project_experiences"]:
            if experience["name"] in exp and '\n'.join(experience["highlights"]) in exp:
                out.append(experience)
                break

    print("Chosen relevant projects", out)
    info_dct["project_experiences"] = out
    return info_dct


def generate_resume(info, job_description):

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
        print(personal_projects)
        cv_out["personal_projects"] = personal_projects

    # TODO - smaller item: add certifications

    # Build the skills section
    cv_out["skills"] = info["skills"]

    # Build the summary
    cv_out["summary"] = info["summary"]

    with open("resume_int.json", 'w') as f:
        json.dump(out, f)

    os.system('rendercv render resume_int.json')


def process_work_descriptions(info_dct, job_description):

    for experience in info_dct["work_experiences"]:
        experience["keywords"] = get_keywords(
            experience["company"],
            experience["position"],
            job_description,
            experience["description"],
        )

        experience["impact"] = get_impact(
            experience["company"],
            experience["position"],
            experience["description"],
            job_description
        )

        experience["highlights"] = [
            *experience["impact"]
        ]

        print("WORK PROCESSING HIGHLIGHTS", experience["highlights"])

    return info_dct


def process_education_descriptions(info_dct):

    for experience in info_dct["education"]:
        experience["highlights"] = [
            f"\\textbf{{Relevant Coursework}}: {', '.join(experience['relevant_coursework'])}"]

        print("HIGHLIGHTS", experience["highlights"])

    return info_dct


def injest_data(data, collection_name, embeddings=OpenAIEmbeddings(), path='./test'):
    qd = Qdrant.from_texts(
        [e.strip() for e in data],
        embeddings,
        path=path,
        collection_name=collection_name
    )

    return qd


# keywords = get_keywords("flockfysh", "Founding AI Engineer", "Built the founding software and concept for an AI system. Led the technical side of the pitch and secured the company a pre-seed round at a $1B valuation. Published an open-source package viewable on PyPI (refyre) to streamline local file management and built a command-line interface allowing customers to access MongoDB and DigitalOcean data.")
# impact = get_impact("flockfysh", "Founding AI Engineer", "Built the founding software and concept for an AI system. Led the technical side of the pitch and secured the company a pre-seed round at a $1B valuation. Published an open-source package viewable on PyPI (refyre) to streamline local file management and built a command-line interface allowing customers to access MongoDB and DigitalOcean data.")
# print(get_short_resume_description("flockfysh", "Founding AI Engineer", "Built the founding software and concept for an AI system. Led the technical side of the pitch and secured the company a pre-seed round at a $1B valuation. Published an open-source package viewable on PyPI (refyre) to streamline local file management and built a command-line interface allowing customers to access MongoDB and DigitalOcean data.", keywords, impact))
with open('experiences.json', 'r') as f:
    info_dct = json.load(f)

# Load in a job description
JOB_NAME = 'ibm'
JOB_DESCRIPTION = load_string(os.getenv("JOB_DESCRIPTION_FILEPATH"))

# Construct our dictionary of info
# Projects pipeline


def format_project(prompt: str, experience: dict):
    return prompt.format(
        name=experience["name"], experience='\n'.join(experience["highlights"]))


def get_resume_in_text(info_dct):
    edup = load_prompt_string('prompts/utils/display/education.prompt')
    projectp = load_prompt_string('prompts/utils/display/project.prompt')
    resumep = load_prompt_string('prompts/utils/display/resume.prompt')
    workp = load_prompt_string('prompts/utils/display/work.prompt')

    edus = '\n\n'.join([edup.format(
        university_name=edu["institution"],
        grad_year=f'{edu["start_date"]} - {edu["end_date"]}',
        coursework=",".join(edu["relevant_coursework"])
    ) for edu in info_dct["education"]])

    works = '\n\n'.join([workp.format(
        company=work["company"],
        role=work["position"],
        time=f'{work["experience_start"]} - {work["experience_end"]}',
        experience=work["description"],
    ) for work in info_dct["work_experiences"]])

    projects = '\n\n'.join([projectp.format(
        title=proj["name"],
        date=proj["date"],
        experience='\n'.join(proj["highlights"]),
    ) for proj in info_dct["project_experiences"]])

    return resumep.format(
        education=edus,
        works=works,
        projects=projects,
        summary=info_dct.get("summary", "No summary provided.")
    )


def extract_variables(template, input_string):
    pattern = re.sub(r'{\w+}', r'(?P<\g<0>>\w+)', re.escape(template))
    match = re.match(pattern, input_string)
    if match:
        return match.groupdict()
    else:
        return {}


def sanitize_for_latex(s: str):
    return s.strip().replace("$", "").replace("%", " percent")


def parse_json_garbage(s):
    s = s[next(idx for idx, c in enumerate(s) if c in "{["):]
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        return json.loads(s[:e.pos])


def resume_text_optimize(job_description, resume_string, llm: OpenAIChatAPI, ITERATIONS=1):

    start_prompt = """
        Act as the hiring manager for this job. 

        {job_description}

        Here is my resume:

        {resume_string}

    """

    continue_prompt = """
        As the hiring manager, do you think that you can improve this resume's content substantially more? It's okay if not. I'd prefer you to start with a hard Yes or No. If Yes, list all the feedback you have.
    """

    implementation_prompt = """
        Now, implement any feedback you propose for the resume
    """

    work_json_prompt = load_prompt_string('prompts/json/work.prompt')
    project_json_prompt = load_prompt_string('prompts/json/project.prompt')
    skills_json_prompt = load_prompt_string('prompts/json/skills.prompt')
    summary_json_prompt = load_prompt_string('prompts/json/summary.prompt')

    # Refinement loop
    p = start_prompt.format(
        job_description=job_description, resume_string=resume_string.strip()).strip()

    llm.prompt_and_response(p)

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

        print()
        print(refined_resume_response)
        print("\n\n")

    # Turn the optimized work section into JSON
    resp = llm.prompt_and_response(work_json_prompt)

    print(resp)

    work_json = parse_json_garbage(resp)
    work_json = work_json["works"]

    for w in work_json:
        w["highlights"] = [sanitize_for_latex(w["description"])]

    # Convert the project section into JSON
    resp = llm.prompt_and_response(project_json_prompt)
    project_json = parse_json_garbage(resp)

    project_json = project_json["projects"]

    for p in project_json:
        p["highlights"] = [sanitize_for_latex(p["description"])]

    # Convert skills into JSON
    resp = llm.prompt_and_response(skills_json_prompt)
    skills_json = parse_json_garbage(resp)

    skills_json = [{"name": s['topic'], "details": s['name']}
                   for s in skills_json["skills"]]

    # Convert summary
    resp = sanitize_for_latex(llm.prompt_and_response(summary_json_prompt).replace(
        "\n", "").strip())

    print(resp)

    return {"works": work_json, "projects": project_json, "skills": skills_json, "summary": resp}


# Work experiences pipeline

# Switch to OpenAIChatAPI() if you want to use the experimental chat API -- note that none of your strings can contain this character: -> " <- .
llm = OpenAIChatAPI()
resume_string = get_resume_in_text(info_dct)
optimized_sections = resume_text_optimize(JOB_DESCRIPTION, resume_string, llm)

info_dct["work_experiences"] = optimized_sections["works"]
print(info_dct["work_experiences"])

info_dct["project_experiences"] = optimized_sections["projects"]
info_dct["skills"] = optimized_sections["skills"]
info_dct["summary"] = optimized_sections["summary"]


def format_work(prompt: str, experience: dict):
    return prompt.format(
        title=experience["position"], company=experience["company"], job_experience=experience["description"])


if os.path.exists('test'):
    shutil.rmtree("test")


with open('experiences2.json', 'w') as f:
    json.dump(info_dct, f)

print("Generating resume", JOB_DESCRIPTION)
generate_resume(info_dct, JOB_DESCRIPTION)
print("Done.")

llm.quit()
