from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
import os
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager

class InfluxDBConnection:
    def __init__(
        self,
        url: Optional[str] = None,
        token: Optional[str] = None,
        org: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        # Use environment variables with defaults
        self.url = url or os.getenv("INFLUXDB_URL", "http://influxdb:8086")
        self.token = token or os.getenv("INFLUXDB_TOKEN", "my-super-secret-auth-token")
        self.org = org or os.getenv("INFLUXDB_ORG", "myorg")
        self.timeout = timeout or int(os.getenv("INFLUXDB_TIMEOUT", "10000"))

    @asynccontextmanager
    async def get_client(self) -> AsyncGenerator[InfluxDBClientAsync, None]:
        """Get an async InfluxDB client"""
        async with InfluxDBClientAsync(
            url=self.url,
            token=self.token,
            org=self.org,
            timeout=self.timeout
        ) as client:
            yield client

    async def write_data(self, bucket: str, record: dict):
        """Write data to InfluxDB"""
        async with self.get_client() as client:
            write_api = client.write_api()
            await write_api.write(bucket=bucket, record=record)

    async def query_data(self, query: str):
        """Query data from InfluxDB"""
        async with self.get_client() as client:
            query_api = client.query_api()
            return await query_api.query(query=query)

    async def get_buckets(self):
        """Get all buckets in the organization"""
        async with self.get_client() as client:
            buckets_api = client.buckets_api()
            return await buckets_api.find_buckets()

    async def delete_data(self, bucket: str, start: str, stop: str, predicate: str = None):
        """Delete data from a bucket within a time range"""
        async with self.get_client() as client:
            delete_api = client.delete_api()
            await delete_api.delete(start, stop, predicate, bucket, self.org)

# Create a singleton instance
influxdb_conn = InfluxDBConnection() 