from datetime import datetime
def format_simulation_time(sim_time):
    """
    Format simulation time to RFC3339 format (ISO 8601 with milliseconds and Z suffix).
    Returns: string in format YYYY-MM-DDTHH:MM:SS.sssZ
    """
    if sim_time is None:
        return None
    
    try:
        if isinstance(sim_time, datetime):
            # Format as ISO 8601 with milliseconds and Z suffix
            return sim_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        elif isinstance(sim_time, str):
            # If already a string, try to parse and reformat
            dt = datetime.fromisoformat(sim_time.rstrip('Z'))
            return dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        else:
            # Fallback to string representation
            return str(sim_time)
    except Exception:
        return str(sim_time)