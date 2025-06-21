from typing import Dict, Optional
from datetime import datetime
from neomodel import db


def report_job(user_uid: str, job_url: str, report_type: str, report_descriptions: str) -> bool:
    """
    Membuat relasi HAS_REPORTED dari User ke Job dengan property reportType, reportDescriptions, reportDate, reportStatus
    
    Args:
        user_uid: User's unique ID
        job_url: URL of the job being reported
        report_type: Type of report (e.g., "Scam", "Inappropriate", etc.)
        report_descriptions: Detailed description of the report
        
    Returns:
        bool: True if report was created successfully, False otherwise
    """
    try:
        # Create or update the HAS_REPORTED relationship
        query = """
            MATCH (u:User {uid: $user_uid}), (j:Job {jobUrl: $job_url})
            MERGE (u)-[r:HAS_REPORTED]->(j)
            SET r.reportType = $report_type,
                r.reportDescriptions = $report_descriptions,
                r.reportDate = $report_date,
                r.reportStatus = $report_status
            RETURN r
        """
        params = {
            "user_uid": user_uid,
            "job_url": job_url,
            "report_type": report_type,
            "report_descriptions": report_descriptions,
            "report_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "report_status": "Perlu Ditinjau",
        }
        
        results, _ = db.cypher_query(query, params)
        return bool(results)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False