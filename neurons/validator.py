# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# TODO(developer): Set your name
# Copyright © 2023 <your name>

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.


import time
import asyncio
import requests
import json
from datetime import datetime

# Bittensor
import bittensor as bt

# import base validator class which takes care of most of the boilerplate
from template.base.validator import BaseValidatorNeuron

# Bittensor Validator Template:
from template.validator import forward


class Validator(BaseValidatorNeuron):
    """
    Audio processing validator that evaluates transcription, TTS, and summarization services.
    This validator rewards miners based on speed, accuracy, and stake, prioritizing the top 5 performers.
    """

    def __init__(self, config=None):
        super(Validator, self).__init__(config=config)

        bt.logging.info("load_state()")
        self.load_state()

        # Proxy server integration settings
        self.proxy_server_url = getattr(self.config, 'proxy_server_url', 'http://localhost:8000')
        self.enable_proxy_integration = getattr(self.config, 'enable_proxy_integration', True)
        self.proxy_check_interval = getattr(self.config, 'proxy_check_interval', 30)  # seconds
        
        # Initialize proxy integration if enabled
        if self.enable_proxy_integration:
            bt.logging.info(f"🔗 Proxy server integration enabled: {self.proxy_server_url}")
            self.last_proxy_check = 0
        else:
            bt.logging.info("⚠️  Proxy server integration disabled")

    async def forward(self):
        """
        Validator forward pass. Consists of:
        - Generating the query
        - Querying the miners
        - Getting the responses
        - Rewarding the miners
        - Updating the scores
        """
        # Check proxy server for tasks if integration is enabled
        if self.enable_proxy_integration:
            await self.check_proxy_server_tasks()
        
        return await forward(self)
    
    async def check_proxy_server_tasks(self):
        """Check proxy server for pending tasks and process them"""
        try:
            current_time = time.time()
            
            # Check if enough time has passed since last check
            if current_time - self.last_proxy_check < self.proxy_check_interval:
                return
            
            self.last_proxy_check = current_time
            
            bt.logging.info("🔍 Checking proxy server for pending tasks...")
            
            # Get integration info from proxy server
            integration_info = await self.get_proxy_integration_info()
            if not integration_info:
                return
            
            # Check if there are pending tasks
            pending_tasks = integration_info.get('pending_tasks', [])
            if not pending_tasks:
                bt.logging.info("📭 No pending tasks in proxy server")
                return
            
            bt.logging.info(f"📋 Found {len(pending_tasks)} pending tasks in proxy server")
            
            # Process pending tasks
            await self.process_proxy_tasks(pending_tasks)
            
        except Exception as e:
            bt.logging.error(f"❌ Error checking proxy server tasks: {str(e)}")
    
    async def get_proxy_integration_info(self):
        """Get integration information from proxy server"""
        try:
            response = requests.get(f"{self.proxy_server_url}/api/v1/validator/integration", timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                bt.logging.warning(f"⚠️  Proxy server returned status {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            bt.logging.warning(f"⚠️  Could not connect to proxy server: {str(e)}")
            return None
    
    async def process_proxy_tasks(self, pending_tasks):
        """Process pending tasks from proxy server"""
        try:
            bt.logging.info(f"🔄 Processing {len(pending_tasks)} tasks from proxy server...")
            
            for task_data in pending_tasks:
                task_id = task_data.get('task_id')
                task_type = task_data.get('task_type')
                language = task_data.get('language')
                
                bt.logging.info(f"📝 Processing task {task_id}: {task_type} ({language})")
                
                # Process the task using the existing forward logic
                await self.process_single_proxy_task(task_data)
                
        except Exception as e:
            bt.logging.error(f"❌ Error processing proxy tasks: {str(e)}")
    
    async def process_single_proxy_task(self, task_data):
        """Process a single task from proxy server"""
        try:
            task_id = task_data.get('task_id')
            task_type = task_data.get('task_type')
            language = task_data.get('language')
            
            bt.logging.info(f"🎯 Processing proxy task: {task_type} in {language}")
            
            # Create AudioTask synapse for this task
            from template.protocol import AudioTask
            
            # Note: We need the actual input_data from the proxy server
            # For now, we'll use a placeholder and log the task
            bt.logging.info(f"📋 Task {task_id} queued for processing:")
            bt.logging.info(f"   - Type: {task_type}")
            bt.logging.info(f"   - Language: {language}")
            bt.logging.info(f"   - Status: Queued for next forward cycle")
            
            # TODO: Integrate with the actual task processing logic
            # This would involve:
            # 1. Getting the actual input_data from proxy server
            # 2. Running the task through miners
            # 3. Evaluating responses
            # 4. Updating the proxy server with results
            
        except Exception as e:
            bt.logging.error(f"❌ Error processing single proxy task: {str(e)}")


# The main function parses the configuration and runs the validator.
if __name__ == "__main__":
    import argparse
    
    # Create argument parser
    parser = argparse.ArgumentParser(description="Bittensor Audio Processing Validator")
    parser.add_argument("--proxy_server_url", type=str, default="http://localhost:8000",
                       help="URL of the proxy server for task integration")
    parser.add_argument("--enable_proxy_integration", action="store_true", default=True,
                       help="Enable integration with proxy server")
    parser.add_argument("--proxy_check_interval", type=int, default=30,
                       help="Interval in seconds to check proxy server for tasks")
    
    # Parse arguments
    args, unknown = parser.parse_known_args()
    
    # Create validator with proxy integration config
    config = type('Config', (), {
        'proxy_server_url': args.proxy_server_url,
        'enable_proxy_integration': args.enable_proxy_integration,
        'proxy_check_interval': args.proxy_check_interval
    })()
    
    with Validator(config) as validator:
        bt.logging.info("🚀 Validator started with proxy server integration")
        bt.logging.info(f"🔗 Proxy server URL: {args.proxy_server_url}")
        bt.logging.info(f"⏱️  Check interval: {args.proxy_check_interval}s")
        
        while True:
            bt.logging.info(f"Validator running... {time.time()}")
            time.sleep(5)
