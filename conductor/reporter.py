"""Results reporter for conductor - handles JSON and text output formats."""

import json
import datetime
import sys
from typing import List, Dict, Any, Optional
from pathlib import Path


class Reporter:
    """Base reporter class."""
    
    def __init__(self, output_file: Optional[str] = None):
        self.output_file = output_file
        self.results = {
            "metadata": {
                "start_time": datetime.datetime.now().isoformat(),
                "end_time": None,
                "total_trials": 0,
                "total_workers": 0
            },
            "trials": []
        }
        self.current_trial = None
        self.current_phase = None
        self.current_worker = None
    
    def start_trials(self, num_trials: int, num_workers: int):
        """Record the start of test trials."""
        self.results["metadata"]["total_trials"] = num_trials
        self.results["metadata"]["total_workers"] = num_workers
    
    def start_trial(self, trial_num: int):
        """Start recording a new trial."""
        self.current_trial = {
            "trial_number": trial_num,
            "start_time": datetime.datetime.now().isoformat(),
            "end_time": None,
            "phases": {}
        }
    
    def end_trial(self):
        """End the current trial."""
        if self.current_trial:
            self.current_trial["end_time"] = datetime.datetime.now().isoformat()
            self.results["trials"].append(self.current_trial)
            self.current_trial = None
    
    def start_phase(self, phase_name: str):
        """Start recording a phase."""
        if self.current_trial:
            self.current_phase = phase_name
            self.current_trial["phases"][phase_name] = {
                "start_time": datetime.datetime.now().isoformat(),
                "end_time": None,
                "workers": {}
            }
    
    def end_phase(self):
        """End the current phase."""
        if self.current_trial and self.current_phase:
            phase_data = self.current_trial["phases"][self.current_phase]
            phase_data["end_time"] = datetime.datetime.now().isoformat()
            self.current_phase = None
    
    def start_worker(self, worker_name: str):
        """Start recording results for a worker."""
        self.current_worker = worker_name
        if self.current_trial and self.current_phase:
            phase_data = self.current_trial["phases"][self.current_phase]
            phase_data["workers"][worker_name] = {
                "start_time": datetime.datetime.now().isoformat(),
                "end_time": None,
                "results": []
            }
    
    def end_worker(self):
        """End recording for the current worker."""
        if self.current_trial and self.current_phase and self.current_worker:
            worker_data = self.current_trial["phases"][self.current_phase]["workers"][self.current_worker]
            worker_data["end_time"] = datetime.datetime.now().isoformat()
            self.current_worker = None
    
    def add_result(self, code: int, message: str):
        """Add a result from the current worker."""
        if self.current_trial and self.current_phase and self.current_worker:
            worker_data = self.current_trial["phases"][self.current_phase]["workers"][self.current_worker]
            worker_data["results"].append({
                "timestamp": datetime.datetime.now().isoformat(),
                "code": code,
                "message": message
            })
    
    def finalize(self):
        """Finalize the report."""
        self.results["metadata"]["end_time"] = datetime.datetime.now().isoformat()
        self.write_output()
    
    def write_output(self):
        """Write the output - to be implemented by subclasses."""
        raise NotImplementedError


class JSONReporter(Reporter):
    """JSON format reporter."""
    
    def write_output(self):
        """Write results as JSON."""
        output = json.dumps(self.results, indent=2)
        
        if self.output_file:
            with open(self.output_file, 'w') as f:
                f.write(output)
        else:
            print(output)


class TextReporter(Reporter):
    """Traditional text format reporter."""
    
    def add_result(self, code: int, message: str):
        """Add a result and print it immediately."""
        super().add_result(code, message)
        # Print in traditional format
        if code == 0 and message.lower() == "done":
            print("done")
        else:
            print(code, message)
    
    def write_output(self):
        """Text reporter writes output incrementally, so nothing to do here."""
        if self.output_file:
            # Write a summary to file
            with open(self.output_file, 'w') as f:
                f.write(f"Conductor Test Results\n")
                f.write(f"=====================\n\n")
                f.write(f"Start Time: {self.results['metadata']['start_time']}\n")
                f.write(f"End Time: {self.results['metadata']['end_time']}\n")
                f.write(f"Total Trials: {self.results['metadata']['total_trials']}\n")
                f.write(f"Total Workers: {self.results['metadata']['total_workers']}\n\n")
                
                for trial in self.results["trials"]:
                    f.write(f"Trial {trial['trial_number']}:\n")
                    for phase_name, phase_data in trial["phases"].items():
                        f.write(f"  Phase: {phase_name}\n")
                        for worker_name, worker_data in phase_data["workers"].items():
                            f.write(f"    Worker: {worker_name}\n")
                            f.write(f"      Results: {len(worker_data['results'])}\n")
                            for result in worker_data["results"]:
                                f.write(f"        Code: {result['code']}, Message: {result['message']}\n")


def create_reporter(format: str, output_file: Optional[str] = None) -> Reporter:
    """Factory function to create appropriate reporter."""
    if format.lower() == 'json':
        return JSONReporter(output_file)
    else:
        return TextReporter(output_file)