import logging
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import google.generativeai as genai
import openai
import json
import random

logger = logging.getLogger(__name__)

class AIService:
    @staticmethod
    def get_provider():
        return getattr(settings, 'AI_PROVIDER', 'mock')

    @classmethod
    def predict_ticket_details(cls, title, description):
        """
        Predicts ticket category and priority based on text description using AI or heuristics.
        """
        provider = cls.get_provider()
        prompt = (
            f"Given the following IT ticket:\n"
            f"Title: {title}\n"
            f"Description: {description}\n\n"
            f"Classify the category into one of these: Hardware, Software, Network, Database, Access, HR, Facilities.\n"
            f"Determine the Priority (Critical, High, Medium, Low).\n"
            f"Determine Urgency (High, Medium, Low).\n"
            f"Determine Impact (High, Medium, Low).\n"
            f"Return JSON format with keys: 'category', 'priority', 'urgency', 'impact'."
        )

        if provider == 'gemini':
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(prompt)
                text = response.text.strip()
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                data = json.loads(text)
                return data
            except Exception as e:
                logger.error(f"Gemini API error in predict_ticket_details: {e}")

        elif provider == 'openai':
            try:
                client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                data = json.loads(response.choices[0].message.content)
                return data
            except Exception as e:
                logger.error(f"OpenAI API error in predict_ticket_details: {e}")

        # Fallback Heuristics
        text = (title + " " + description).lower()
        
        category = 'Software'
        if any(w in text for w in ['router', 'switch', 'network', 'wifi', 'internet', 'offline']):
            category = 'Network'
        elif any(w in text for w in ['laptop', 'pc', 'mouse', 'monitor', 'keyboard', 'hardware']):
            category = 'Hardware'
        elif any(w in text for w in ['database', 'query', 'sql', 'postgres', 'slow load']):
            category = 'Database'
        elif any(w in text for w in ['password', 'reset', 'access', 'login', 'permission']):
            category = 'Access'
        elif any(w in text for w in ['leave', 'holiday', 'payroll', 'hr']):
            category = 'HR'

        priority = 'Medium'
        urgency = 'Medium'
        impact = 'Medium'
        if any(w in text for w in ['completely offline', 'down', 'critical', 'emergency', 'broken', 'breached']):
            priority = 'CRITICAL'
            urgency = 'HIGH'
            impact = 'HIGH'
        elif any(w in text for w in ['slow', 'delay', 'issue', 'warning']):
            priority = 'HIGH'
            urgency = 'MEDIUM'
            impact = 'MEDIUM'
        elif any(w in text for w in ['minor', 'typo', 'how to', 'question']):
            priority = 'LOW'
            urgency = 'LOW'
            impact = 'LOW'

        return {
            'category': category,
            'priority': priority.upper(),
            'urgency': urgency.upper(),
            'impact': impact.upper()
        }

    @classmethod
    def suggest_resolution(cls, title, description):
        """
        Suggests resolution and logs root cause analysis.
        """
        provider = cls.get_provider()
        prompt = (
            f"Generate a recommended resolution plan and root cause analysis for the following issue:\n"
            f"Title: {title}\n"
            f"Description: {description}\n\n"
            f"Return JSON format with keys: 'suggested_resolution', 'root_cause'."
        )

        if provider == 'gemini':
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(prompt)
                text = response.text.strip()
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                return json.loads(text)
            except Exception as e:
                logger.error(f"Gemini error in suggest_resolution: {e}")

        elif provider == 'openai':
            try:
                client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                return json.loads(response.choices[0].message.content)
            except Exception as e:
                logger.error(f"OpenAI error in suggest_resolution: {e}")

        # Fallback Heuristics
        text = (title + " " + description).lower()
        if 'network' in text or 'router' in text or 'wifi' in text:
            return {
                'suggested_resolution': 'Perform a hard reboot on the core network router. Check interface cables and verify routing tables on the subnet controller.',
                'root_cause': 'Port overload due to high broadcast traffic or hardware thermal throttling.'
            }
        elif 'database' in text or 'slow' in text or 'query' in text:
            return {
                'suggested_resolution': 'Analyze running queries, add missing indexes on high-frequency where-clauses, and scale up the database connection pool settings.',
                'root_cause': 'Unoptimized table joins causing full table scans and high CPU locking.'
            }
        elif 'access' in text or 'login' in text or 'password' in text:
            return {
                'suggested_resolution': 'Reset AD account password or sync security groups, then clear browser session and cookies and re-login.',
                'root_cause': 'Credential caching mismatch or replication delay in Active Directory domain controller.'
            }
        return {
            'suggested_resolution': 'Investigate local logs. Reinstall the affected package/application, restart standard processes, and verify configuration parameters.',
            'root_cause': 'Generic configuration file corruption or unhandled runtime exception.'
        }

    @classmethod
    def predict_sla_breach(cls, incident):
        """
        Calculates probability of SLA breach based on agent load and deadline.
        """
        time_left = incident.sla_due - timezone.now() if incident.sla_due else timedelta(hours=10)
        if time_left.total_seconds() < 0:
            return True, 100.0
        
        probability = 10.0
        if incident.priority == 'CRITICAL' and incident.status == 'NEW':
            probability += 50.0
        elif incident.priority == 'HIGH' and incident.status == 'NEW':
            probability += 30.0
        
        if incident.assigned_to:
            ticket_count = incident.assigned_to.assigned_incidents.filter(status__in=['NEW', 'IN_PROGRESS']).count()
            probability += min(ticket_count * 10, 30)

        if time_left.total_seconds() < 3600:
            probability += 40.0
        
        prob = min(probability, 99.0)
        return prob > 70.0, prob

    @classmethod
    def get_chat_response(cls, messages_list):
        """
        Generates conversational response using chat context history.
        """
        provider = cls.get_provider()
        
        history_str = ""
        for msg in messages_list:
            role = "Employee" if msg['sender'] == 'USER' else "Assistant"
            history_str += f"{role}: {msg['message']}\n"
        
        prompt = (
            f"You are an AI IT Operations Desk assistant for Enterprise Platform. "
            f"Help the user solve their issue, create incidents, check asset statuses, or guide them on workflow approvals. "
            f"Keep your response helpful, friendly, and under 3 sentences.\n\n"
            f"Conversation History:\n{history_str}\n"
            f"Assistant:"
        )

        if provider == 'gemini':
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(prompt)
                return response.text.strip()
            except Exception as e:
                logger.error(f"Gemini chat response error: {e}")

        elif provider == 'openai':
            try:
                client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                api_messages = [{"role": "system", "content": "You are a helpful IT helpdesk assistant."}]
                for msg in messages_list:
                    role_map = "user" if msg['sender'] == 'USER' else "assistant"
                    api_messages.append({"role": role_map, "content": msg['message']})
                
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=api_messages
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"OpenAI chat response error: {e}")

        # Fallback Mock Responses
        last_message = messages_list[-1]['message'].lower() if messages_list else ""
        
        # Greetings
        if any(w in last_message for w in ['hello', 'hi', 'hey', 'namaste']):
            return "Hello! I am your AI Operations Assistant for this AIOPS Platform. I can guide you through our smart ticketing, automated leave/asset approvals, SLA compliance tracking, or asset management. How can I help you today?"
        
        # Questions about the Project generally
        elif any(w in last_message for w in ['project', 'what is', 'tell me', 'about', 'platform', 'features', 'details', 'work']):
            return "This is the **AIOPS Platform** (AI-Powered Enterprise Operations Platform), a modern command center that automates IT support and enterprise workflows. It integrates smart incident management, automated approvals (leaves/laptops), live SLA compliance analytics, and corporate asset tracking into one unified, beautiful dashboard."
        
        # Questions about Incidents / Ticketing
        elif any(w in last_message for w in ['incident', 'ticket', 'trouble', 'create', 'problem', 'change']):
            return "Our **Smart Incidents System** allows employees to report issues. Machine learning models automatically predict the category (Network, Hardware, Software, etc.) and priority, auto-assign the ticket to available agents, and suggest resolution plans and root cause analysis!"
        
        # Questions about Approvals / Workflows / Leaves
        elif any(w in last_message for w in ['approval', 'request', 'workflow', 'leave', 'vacation', 'manager', 'admin']):
            return "We support **Automated Approval Workflows** for leave requests, hardware allocation, and software installations. Submissions route dynamically to the Department Manager, then to the Administrator for final execution, sending real-time in-app notifications at each step."
        
        # Questions about SLA
        elif any(w in last_message for w in ['sla', 'breach', 'resolution', 'compliance', 'analytics']):
            return "The **Live SLA Tracking** system monitors incident deadlines. The Executive Dashboard aggregates active SLA rates, average resolution times, and alerts administrators of high-risk tickets to prevent breaches proactively."
        
        # Questions about Assets
        elif any(w in last_message for w in ['asset', 'laptop', 'inventory', 'hardware', 'allocate']):
            return "Our **IT Asset Management** system tracks corporate assets from procurement to retirement. When a hardware request is approved, the system dynamically registers it, allocates it to the employee, and updates connecting records automatically."
        
        # Questions about VPN
        elif 'vpn' in last_message:
            return "To connect to the corporate VPN, download the GlobalProtect client, set the gateway URL to 'vpn.enterprise.com', and authenticate using your Employee AD credentials. Don't forget to approve the MFA prompt."
        
        # Creator / Developer questions
        elif any(w in last_message for w in ['developer', 'creator', 'author', 'pujitha', 'who made']):
            return "This state-of-the-art enterprise command center was custom-developed for Pujitha Kollaparthi (Administrator) to automate and manage complex IT operations."
            
        # Help list
        elif any(w in last_message for w in ['help', 'guide', 'commands', 'what can you do']):
            return "I can answer questions about the **AIOPS Platform**! Ask me about logging incidents (auto category & priority), approval chains for leaves, VPN connection steps, SLA metrics, or laptop allocations."

        # Default fallback
        return "I can help you with the **AIOPS Platform**! This project automates enterprise IT operations using AI-driven ticketing, Manager/Admin leave & asset approval chains, live SLA tracking, and IT asset allocation. Please ask me any specific question about this project!"

    @classmethod
    def predict_infrastructure_outage(cls, cpu, memory, disk, network):
        """
        Predicts probability of an outage based on server hardware parameters.
        """
        provider = cls.get_provider()
        prompt = (
            f"Analyze this server telemetric event:\n"
            f"- CPU Usage: {cpu}%\n"
            f"- Memory Usage: {memory}%\n"
            f"- Disk Space: {disk}%\n"
            f"- Network Load: {network} Mbps\n\n"
            f"Predict the Outage Probability (%) in the next 2 hours.\n"
            f"Formulate a warning explanation and a recommended proactive IT ticket description.\n"
            f"Return JSON with keys: 'probability' (int), 'reason' (str), 'recommendation' (str)."
        )

        if provider == 'gemini':
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(prompt)
                text = response.text.strip()
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                return json.loads(text)
            except Exception as e:
                logger.error(f"Gemini error in predict_infrastructure_outage: {e}")

        elif provider == 'openai':
            try:
                client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                return json.loads(response.choices[0].message.content)
            except Exception as e:
                logger.error(f"OpenAI error in predict_infrastructure_outage: {e}")

        # Heuristic Fallback
        probability = 5.0
        if cpu > 90:
            probability += 40.0
        if memory > 90:
            probability += 35.0
        if disk > 85:
            probability += 10.0
        if network > 800:
            probability += 9.0
            
        probability = min(probability, 99.0)
        
        reason = "All metrics are performing within normal operational thresholds."
        recommendation = "No preventive action is required at this time."
        
        if probability >= 75.0:
            reason = f"Critical levels detected: CPU ({cpu}%) and Memory ({memory}%) are exhausting rapidly, creating an imminent crash risk due to thread saturation."
            recommendation = f"PROACTIVE WORK REQUIRED: Expand database connection pools, verify process locks, clean up temp storage mounts on Prod-Server, and scale memory resources."
        elif probability >= 40.0:
            reason = f"Warning levels detected: Metrics show elevated CPU ({cpu}%) and heavy network loads ({network} Mbps), which could lead to severe delay or performance degradation."
            recommendation = "Monitor system logs closely. Schedule disk cleanup and review unoptimized database queries."

        return {
            'probability': int(probability),
            'reason': reason,
            'recommendation': recommendation
        }

