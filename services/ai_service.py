import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = None
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if OPENAI_API_KEY and OPENAI_API_KEY != "sk-your-openai-api-key-here":
    client = OpenAI(api_key=OPENAI_API_KEY)


def _call_openai(system_prompt: str, user_prompt: str) -> str:
    if not client:
        return json.dumps({"error": "OpenAI API key not configured. Please set OPENAI_API_KEY in .env"})
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=4000,
        )
        return response.choices[0].message.content
    except Exception as e:
        return json.dumps({"error": f"OpenAI API error: {str(e)}"})


def match_jobs_for_employee(employee_profile: dict, vacancies: list[dict]) -> list[dict]:
    system_prompt = """Ты — AI-рекрутер. Тебе дан профиль сотрудника и список вакансий.
Проанализируй совпадение каждой вакансии с профилем сотрудника.
Верни JSON-массив объектов, отсортированный по проценту совпадения (от большего к меньшему).
Каждый объект должен содержать:
- vacancy_id (int)
- match_percent (int, 0-100)
- explanation (string, краткое объяснение на русском)
Верни ТОЛЬКО JSON-массив, без markdown-обёртки."""

    user_prompt = f"""Профиль сотрудника:
{json.dumps(employee_profile, ensure_ascii=False)}

Вакансии:
{json.dumps(vacancies, ensure_ascii=False)}"""

    result = _call_openai(system_prompt, user_prompt)
    try:
        parsed = json.loads(result)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "error" in parsed:
            return [{"error": parsed["error"]}]
        return []
    except json.JSONDecodeError:
        try:
            start = result.find("[")
            end = result.rfind("]") + 1
            if start != -1 and end > start:
                return json.loads(result[start:end])
        except Exception:
            pass
        return [{"error": "Не удалось разобрать ответ AI"}]


def match_candidates_for_vacancy(vacancy: dict, candidates: list[dict]) -> list[dict]:
    system_prompt = """Ты — AI-рекрутер. Тебе дана вакансия и список кандидатов.
Проанализируй совпадение каждого кандидата с вакансией.
Верни JSON-массив объектов, отсортированный по проценту совпадения (от большего к меньшему).
Каждый объект должен содержать:
- candidate_id (int)
- match_percent (int, 0-100)
- explanation (string, краткое обоснование на русском)
Верни ТОЛЬКО JSON-массив, без markdown-обёртки."""

    user_prompt = f"""Вакансия:
{json.dumps(vacancy, ensure_ascii=False)}

Кандидаты:
{json.dumps(candidates, ensure_ascii=False)}"""

    result = _call_openai(system_prompt, user_prompt)
    try:
        parsed = json.loads(result)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "error" in parsed:
            return [{"error": parsed["error"]}]
        return []
    except json.JSONDecodeError:
        try:
            start = result.find("[")
            end = result.rfind("]") + 1
            if start != -1 and end > start:
                return json.loads(result[start:end])
        except Exception:
            pass
        return [{"error": "Не удалось разобрать ответ AI"}]


def generate_employment_contract(contract_data: dict) -> str:
    system_prompt = """Ты — юрист-кадровик. Сгенерируй полный трудовой договор на русском языке
на основе предоставленных данных. Договор должен содержать все стандартные разделы:
предмет договора, права и обязанности сторон, оплата труда, рабочее время,
испытательный срок (если указан), условия расторжения и т.д.
Верни только текст договора, без markdown-разметки."""

    user_prompt = f"Данные для трудового договора:\n{json.dumps(contract_data, ensure_ascii=False)}"
    return _call_openai(system_prompt, user_prompt)


def summarize_reports(reports: list[dict]) -> str:
    system_prompt = """Ты — HR-аналитик. Тебе даны отчёты сотрудников за определённый период.
Создай краткое, структурированное резюме на русском языке:
1. Общие достижения команды
2. Основные блокеры и проблемы
3. Планы на следующий период
4. Рекомендации
Пиши кратко и по делу."""

    user_prompt = f"Отчёты сотрудников:\n{json.dumps(reports, ensure_ascii=False)}"
    return _call_openai(system_prompt, user_prompt)
