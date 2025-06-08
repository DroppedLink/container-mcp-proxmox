"""Task and job management service for Proxmox."""

import logging
from typing import List, Dict, Any, Optional
from .base_service import BaseProxmoxService

logger = logging.getLogger(__name__)


class TaskService(BaseProxmoxService):
    """Service for managing Proxmox tasks and jobs."""

    def list_tasks(self, node: str = "", limit: int = 20, running_only: bool = False) -> List[Dict[str, Any]]:
        """List recent tasks on node(s)."""
        try:
            all_tasks = []
            
            # If specific node provided, check only that node
            if node:
                nodes_to_check = [node]
            else:
                # Get all nodes
                nodes_list = self.proxmox.nodes.get()
                nodes_to_check = [n['node'] for n in nodes_list]
            
            for node_name in nodes_to_check:
                try:
                    # Get tasks from node
                    tasks = self.proxmox.nodes(node_name).tasks.get(limit=limit)
                    
                    for task in tasks:
                        task_info = {
                            'node': node_name,
                            'upid': task.get('upid', ''),
                            'type': task.get('type', 'unknown'),
                            'id': task.get('id', ''),
                            'user': task.get('user', ''),
                            'status': task.get('status', 'unknown'),
                            'starttime': task.get('starttime', 0),
                            'endtime': task.get('endtime', 0),
                            'pid': task.get('pid', 0),
                            'pstart': task.get('pstart', 0)
                        }
                        
                        # Calculate duration
                        if task_info['endtime'] > 0:
                            duration = task_info['endtime'] - task_info['starttime']
                            task_info['duration'] = duration
                            task_info['duration_human'] = self._format_duration(duration)
                        else:
                            task_info['duration'] = None
                            task_info['duration_human'] = "Running" if task_info['status'] == 'running' else "Unknown"
                        
                        # Format start time
                        task_info['starttime_human'] = self._format_timestamp(task_info['starttime'])
                        
                        # Filter running tasks if requested
                        if running_only and task_info['status'] != 'running':
                            continue
                        
                        all_tasks.append(task_info)
                        
                except Exception as e:
                    logger.error(f"Error getting tasks for node {node_name}: {e}")
                    continue
            
            # Sort by start time (newest first)
            all_tasks.sort(key=lambda x: x['starttime'], reverse=True)
            
            # Apply limit across all nodes
            return all_tasks[:limit]
            
        except Exception as e:
            logger.error(f"Failed to list tasks: {e}")
            raise

    def get_task_status(self, node: str, upid: str) -> Dict[str, Any]:
        """Get detailed status and logs for a specific task."""
        try:
            # Get task status
            task_status = self.proxmox.nodes(node).tasks(upid).status.get()
            
            # Get task log
            try:
                task_log = self.proxmox.nodes(node).tasks(upid).log.get()
                log_lines = [entry.get('t', '') for entry in task_log if 't' in entry]
            except Exception:
                log_lines = ["Log not available"]
            
            result = {
                'upid': upid,
                'node': node,
                'type': task_status.get('type', 'unknown'),
                'id': task_status.get('id', ''),
                'user': task_status.get('user', ''),
                'status': task_status.get('status', 'unknown'),
                'exitstatus': task_status.get('exitstatus', ''),
                'starttime': task_status.get('starttime', 0),
                'endtime': task_status.get('endtime', 0),
                'pid': task_status.get('pid', 0),
                'pstart': task_status.get('pstart', 0),
                'log_lines': log_lines
            }
            
            # Calculate duration
            if result['endtime'] > 0:
                duration = result['endtime'] - result['starttime']
                result['duration'] = duration
                result['duration_human'] = self._format_duration(duration)
            else:
                result['duration'] = None
                result['duration_human'] = "Running" if result['status'] == 'running' else "Unknown"
            
            # Format timestamps
            result['starttime_human'] = self._format_timestamp(result['starttime'])
            result['endtime_human'] = self._format_timestamp(result['endtime']) if result['endtime'] > 0 else "Not finished"
            
            # Get recent log lines (last 20)
            result['recent_log'] = log_lines[-20:] if log_lines else []
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get task status for {upid} on {node}: {e}")
            raise

    def cancel_task(self, node: str, upid: str) -> Dict[str, Any]:
        """Cancel a running task."""
        try:
            # Check if task is still running
            task_status = self.proxmox.nodes(node).tasks(upid).status.get()
            
            if task_status.get('status') != 'running':
                return {
                    'status': 'error',
                    'message': f"Task {upid} is not running (status: {task_status.get('status')})"
                }
            
            # Stop the task
            self.proxmox.nodes(node).tasks(upid).stop.post()
            
            return {
                'status': 'success',
                'message': f"Cancel request sent for task {upid}",
                'upid': upid,
                'node': node
            }
            
        except Exception as e:
            logger.error(f"Failed to cancel task {upid} on {node}: {e}")
            raise

    def list_backup_jobs(self, node: str = "") -> List[Dict[str, Any]]:
        """List scheduled backup jobs."""
        try:
            backup_jobs = []
            
            # If specific node provided, check only that node
            if node:
                nodes_to_check = [node]
            else:
                # Get all nodes
                nodes_list = self.proxmox.nodes.get()
                nodes_to_check = [n['node'] for n in nodes_list]
            
            for node_name in nodes_to_check:
                try:
                    # Get backup jobs (vzdump jobs)
                    cron_jobs = self.proxmox.nodes(node_name).cron.get()
                    
                    for job in cron_jobs:
                        # Filter for backup jobs
                        if job.get('type') == 'vzdump':
                            job_info = {
                                'node': node_name,
                                'id': job.get('id', ''),
                                'schedule': job.get('schedule', ''),
                                'enabled': job.get('enabled', 0) == 1,
                                'comment': job.get('comment', ''),
                                'user': job.get('user', ''),
                                'mailto': job.get('mailto', ''),
                                'storage': job.get('storage', ''),
                                'vmid': job.get('vmid', ''),
                                'node_restrict': job.get('node', ''),
                                'compress': job.get('compress', ''),
                                'mode': job.get('mode', ''),
                                'exclude': job.get('exclude', ''),
                                'pool': job.get('pool', ''),
                                'quiet': job.get('quiet', 0) == 1,
                                'stop': job.get('stop', 0) == 1,
                                'suspend': job.get('suspend', 0) == 1
                            }
                            
                            backup_jobs.append(job_info)
                            
                except Exception as e:
                    logger.error(f"Error getting backup jobs for node {node_name}: {e}")
                    continue
            
            return backup_jobs
            
        except Exception as e:
            logger.error(f"Failed to list backup jobs: {e}")
            raise

    def create_backup_job(self, node: str, schedule: str, vmid: str = "", 
                         storage: str = "local", enabled: bool = True,
                         comment: str = "", mailto: str = "", compress: str = "zstd",
                         mode: str = "snapshot") -> Dict[str, Any]:
        """Create a new scheduled backup job."""
        try:
            job_config = {
                'type': 'vzdump',
                'schedule': schedule,
                'enabled': 1 if enabled else 0,
                'storage': storage,
                'compress': compress,
                'mode': mode
            }
            
            if vmid:
                job_config['vmid'] = vmid
            if comment:
                job_config['comment'] = comment
            if mailto:
                job_config['mailto'] = mailto
            
            # Create the backup job
            result = self.proxmox.nodes(node).cron.post(**job_config)
            
            return {
                'status': 'success',
                'message': f"Backup job created successfully",
                'job_id': result,
                'node': node,
                'schedule': schedule
            }
            
        except Exception as e:
            logger.error(f"Failed to create backup job on {node}: {e}")
            raise

    def delete_backup_job(self, node: str, job_id: str) -> Dict[str, Any]:
        """Delete a scheduled backup job."""
        try:
            # Delete the backup job
            self.proxmox.nodes(node).cron(job_id).delete()
            
            return {
                'status': 'success',
                'message': f"Backup job {job_id} deleted successfully",
                'job_id': job_id,
                'node': node
            }
            
        except Exception as e:
            logger.error(f"Failed to delete backup job {job_id} on {node}: {e}")
            raise

    def update_backup_job(self, node: str, job_id: str, **kwargs) -> Dict[str, Any]:
        """Update an existing backup job."""
        try:
            # Update the backup job
            self.proxmox.nodes(node).cron(job_id).post(**kwargs)
            
            return {
                'status': 'success',
                'message': f"Backup job {job_id} updated successfully",
                'job_id': job_id,
                'node': node
            }
            
        except Exception as e:
            logger.error(f"Failed to update backup job {job_id} on {node}: {e}")
            raise

    def _format_duration(self, duration_seconds: int) -> str:
        """Format duration in human-readable format."""
        if duration_seconds < 60:
            return f"{duration_seconds}s"
        elif duration_seconds < 3600:
            minutes = duration_seconds // 60
            seconds = duration_seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = duration_seconds // 3600
            minutes = (duration_seconds % 3600) // 60
            return f"{hours}h {minutes}m"

    def _format_timestamp(self, timestamp: int) -> str:
        """Format Unix timestamp in human-readable format."""
        if timestamp == 0:
            return "Not started"
        
        try:
            from datetime import datetime
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return f"Timestamp: {timestamp}" 