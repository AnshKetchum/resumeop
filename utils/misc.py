import shutil
import os
import json
import re

from langchain.vectorstores.qdrant import Qdrant
from langchain.chat_models.openai import ChatOpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
import openai

from dotenv import load_dotenv

from utils.LLM import OpenAIChatAPI, OpenAIBackendAPI, LLMAPI

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
    info["work_experiences"] = out
    return info


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
    info[info_attr] = out
    return info


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
    info["project_experiences"] = out
    return info


def injest_data(data, collection_name, embeddings=OpenAIEmbeddings(), path='./test'):
    qd = Qdrant.from_texts(
        [e.strip() for e in data],
        embeddings,
        path=path,
        collection_name=collection_name
    )

    return qd


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
