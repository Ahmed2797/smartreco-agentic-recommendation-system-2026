import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from src.database.db import SessionLocal
from src.database import models
from src.agent.langgraph_agent import run_agentic_recommendation
from src.utils.helper import send_email_digest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SmartReco-Scheduler")

# Background Scheduler Instance
scheduler = BackgroundScheduler()

def process_and_send_daily_digests():
    """
    Daily Proactive Recommendation Digest Cron Job:
    1. Fetch all users from the database.
    2. For each user, retrieve their recent activity events.
    3. Run the LangGraph Explicit Reasoning Agent to generate a personalized recommendation narrative and recommended product IDs.
    """
    logger.info("🚀 Starting Daily Proactive Recommendation Digest Cron Job...")
    db: Session = SessionLocal()

    try:
        users = db.query(models.User).filter(models.User.role == "user").all()

        for user in users:
            # Fetch recent tracked events for the user
            events = db.query(models.ActivityEvent).filter_by(user_id=user.id).all()
            formatted_events = [{"event_type": e.event_type, "event_data": e.event_data} for e in events]

            if not formatted_events:
                logger.info(f"Skipping User {user.id} ({user.email}): No behavior activity recorded.")
                continue

            # Run LangGraph Explicit Reasoning Agent
            ai_result = run_agentic_recommendation(user_id=user.id, user_events=formatted_events)
            narrative = ai_result.get("narrative", "")
            product_ids = ai_result.get("recommended_product_ids", [])

            # Fetch Product Details from DB
            recommended_products = db.query(models.Product).filter(models.Product.id.in_(product_ids)).all()

            # Construct HTML Email Template
            product_list_html = "".join([
                f"""
                <li style="margin-bottom: 12px; padding: 10px; border: 1px solid #e2e8f0; border-radius: 6px;">
                    <strong style="font-size: 16px; color: #1e293b;">{p.title}</strong> (${p.price})<br>
                    <span style="color: #64748b; font-size: 14px;">{p.category}</span>
                    <p style="margin: 4px 0 0 0; color: #334155;">{p.description}</p>
                </li>
                """ for p in recommended_products
            ])

            html_body = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #0f172a;">
                <h2 style="color: #2563eb;">🎯 Your Daily Learning Digest</h2>
                <div style="background-color: #f8fafc; border-left: 4px solid #2563eb; padding: 15px; border-radius: 4px; margin-bottom: 20px;">
                    <p style="font-style: italic; font-size: 15px; margin: 0;">"{narrative}"</p>
                </div>
                <h3>Recommended Courses Based on Your Activity:</h3>
                <ul style="list-style: none; padding-left: 0;">
                    {product_list_html if product_list_html else "<li>Check out our trending platform courses!</li>"}
                </ul>
                <hr style="border: none; border-top: 1px solid #e2e8f0; margin-top: 20px;">
                <p style="font-size: 12px; color: #94a3b8; text-align: center;">SmartReco AI Platform • Automated Recommendation Engine</p>
            </div>
            """

            # Save generated recommendation to DB history
            db_rec = models.Recommendation(
                user_id=user.id,
                narrative=narrative,
                recommended_product_ids=product_ids
            )
            db.add(db_rec)
            db.commit()

            # Send Email Digest
            send_email_digest(
                to_email=user.email,
                subject="💡 Personal Recommendation Digest for Your Learning Goals",
                html_content=html_body
            )

    except Exception as e:
        logger.error(f"Error executing proactive daily digest job: {str(e)}")
    finally:
        db.close()


def start_scheduler():
    """FastAPI setup background scheduler for daily proactive recommendation digests."""
    # Cron Job: Daily at 5:00 PM (17:00)
    scheduler.add_job(
        process_and_send_daily_digests,
        trigger=CronTrigger(hour=17, minute=0),
        id="daily_recommendation_digest",
        replace_existing=True
    )
    scheduler.start()
    logger.info("⏰ APScheduler initialized and running background cron jobs!")


def shutdown_scheduler():
    """FastAPI shutdown function to stop the scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("🛑 APScheduler stopped successfully.")