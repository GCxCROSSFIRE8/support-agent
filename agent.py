import pandas as pd
import re
from langchain_community.document_loaders import TextLoader

 
def clean_text(text):
    return re.sub(r"[^\w\s]", "", text.lower())


def build_vectorstore():
    docs = []

    for file in ["hackerrank.txt", "claude.txt", "visa.txt"]:
        loader = TextLoader(f"support_docs/{file}")
        docs.extend(loader.load())

    return docs


def classify_request(issue):
    text = issue.lower()

    if any(x in text for x in ["refund", "charged", "payment", "billing"]):
        return "product_issue", "billing"

    if any(x in text for x in ["error", "bug", "not working", "fail"]):
        return "bug", "technical"

    if any(x in text for x in ["feature", "request", "add"]):
        return "feature_request", "feature"

    if any(x in text for x in ["login", "account", "password"]):
        return "product_issue", "account"

    if len(text.strip()) < 5:
        return "invalid", "unknown"

    return "product_issue", "general"


def detect_risk(issue):
    text = issue.lower()

    high_risk = [
        "fraud", "hacked", "stolen", "unauthorized",
        "urgent", "immediately", "blocked", "suspended"
    ]

    return any(word in text for word in high_risk)


def retrieve_context(docs, query):
    query_words = set(clean_text(query).split())
    scored = []

    for doc in docs:
        content = doc.page_content
        content_clean = clean_text(content)
        content_words = set(content_clean.split())

        score = len(query_words & content_words)

        if score >= 2:
            scored.append((score, content))

    scored.sort(reverse=True, key=lambda x: x[0])

    return "\n".join([text for _, text in scored[:2]])


def decide(request_type, risk, context):
    if risk:
        return "escalated"

    if request_type == "invalid":
        return "replied"

    if not context or len(context.strip()) < 30:
        return "escalated"

    return "replied"


def generate_response(issue, context):
    if not context:
        return "I cannot find this information in the support documents."

    issue_words = set(clean_text(issue).split())
    best_line = ""
    best_score = 0

    for line in context.split("\n"):
        clean_line = line.strip()

      
        if len(clean_line) < 20 or clean_line.endswith(":"):
            continue

        line_words = set(clean_text(clean_line).split())
        score = len(issue_words & line_words)

        if score > best_score:
            best_score = score
            best_line = clean_line

    if best_line:
        return best_line


    return "Relevant information found, but unable to extract a precise answer."


def run():
    print("Loading documents...")
    docs = build_vectorstore()

    print("Reading CSV...")
    df = pd.read_csv("support_tickets.csv")

    outputs = []

    with open("log.txt", "w", encoding="utf-8") as log_file:

        for _, row in df.iterrows():
            issue = str(row["Issue"])
            subject = str(row["Subject"])
            company = str(row["Company"])

            full_text = issue + " " + subject

            request_type, product_area = classify_request(full_text)
            risk = detect_risk(full_text)

            context = retrieve_context(docs, full_text)
            status = decide(request_type, risk, context)

            if status == "replied":
                response = generate_response(full_text, context)
            else:
                response = "This issue has been escalated to a human support agent due to risk or insufficient information."

            justification = f"Classified as {request_type}, risk={risk}, context_length={len(context)}"

            # Logging
            log_file.write(f"Issue: {issue}\n")
            log_file.write(f"Subject: {subject}\n")
            log_file.write(f"Company: {company}\n")
            log_file.write(f"Request Type: {request_type}\n")
            log_file.write(f"Product Area: {product_area}\n")
            log_file.write(f"Status: {status}\n")
            log_file.write(f"Response: {response}\n")
            log_file.write(f"Justification: {justification}\n")
            log_file.write("=" * 50 + "\n")

            outputs.append({
                "status": status,
                "product_area": product_area,
                "response": response,
                "justification": justification,
                "request_type": request_type
            })

    pd.DataFrame(outputs).to_csv("output.csv", index=False)

    print("Done! Output saved to output.csv and log.txt")

if __name__ == "__main__":
    run()