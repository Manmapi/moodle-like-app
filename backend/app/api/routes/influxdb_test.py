from fastapi import APIRouter
from app.core.influxdb import influxdb_conn
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from pydantic import BaseModel
from typing import Optional, Dict

router = APIRouter(prefix="/influxdb", tags=["influxdb"])

class WriteDataRequest(BaseModel):
    bucket: str
    measurement: str
    fields: Dict[str, float]
    tags: Optional[Dict[str, str]] = None

@router.get("/buckets")
async def get_buckets():
    """Get list of all buckets in the organization"""
    buckets = await influxdb_conn.get_buckets()
    return [{"name": bucket.name, "id": bucket.id} for bucket in buckets.buckets]

@router.post("/write-data")
async def write_data(data: WriteDataRequest):
    """Write data to a specific bucket"""
    # Create the data point
    point = {
        "measurement": data.measurement,
        "fields": data.fields,
    }
    if data.tags:
        point["tags"] = data.tags
    
    # Write the data
    await influxdb_conn.write_data(bucket=data.bucket, record=point)
    return {"status": "success", "message": f"Data written to {data.bucket}"}

@router.get("/query-data")
async def query_data(
    bucket: str,
    measurement: str,
    start: str = "-1h"
):
    """Query data from a specific bucket and measurement"""
    # Build the query
    query = f'''
        from(bucket: "{bucket}")
            |> range(start: {start})
            |> filter(fn: (r) => r["_measurement"] == "{measurement}")
    '''
    
    # Execute the query
    result = await influxdb_conn.query_data(query=query)
    
    # Process the results
    data = []
    for table in result:
        for record in table.records:
            data.append({
                "time": record.get_time(),
                "measurement": record.get_measurement(),
                "field": record.get_field(),
                "value": record.get_value(),
                "tags": record.values
            })
    
    return {"data": data}

@router.delete("/delete-data")
async def delete_data(
    bucket: str,
    start: str,
    stop: str,
    predicate: str = None
):
    """Delete data from a bucket within a time range"""
    await influxdb_conn.delete_data(
        bucket=bucket,
        start=start,
        stop=stop,
        predicate=predicate
    )
    
    return {
        "status": "success",
        "message": f"Data deleted from {bucket} between {start} and {stop}"
    } 