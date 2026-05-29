import re


class ProgressParser:
    def __init__(self, audio_duration=0):
        self.audio_duration = audio_duration
        self.stage = "initializing"
        self.stages = [
            ("loading_model", "Loading model..."),
            ("moving_to_device", "Moving model to device..."),
            ("processing", "Processing audio..."),
            ("saving", "Saving stems..."),
            ("done", "Complete!"),
        ]
        self.current_stage_idx = 0
        self.stage_weights = [5, 5, 70, 18, 2]

    def parse_line(self, line):
        line_lower = line.lower()

        if "loading" in line_lower and "model" in line_lower:
            self.stage = "loading_model"
        elif "moving" in line_lower or "device" in line_lower:
            self.stage = "moving_to_device"
        elif "separ" in line_lower or "process" in line_lower or "track" in line_lower:
            self.stage = "processing"
        elif "saving" in line_lower or "writing" in line_lower or "export" in line_lower:
            self.stage = "saving"
        elif "done" in line_lower or "complete" in line_lower or "finished" in line_lower:
            self.stage = "done"

        progress = self._compute_progress(line)
        return progress, self._current_status()

    def _current_status(self):
        for name, label in self.stages:
            if name == self.stage:
                return label
        return "Working..."

    def _compute_progress(self, line):
        base = sum(
            self.stage_weights[i]
            for i, (name, _) in enumerate(self.stages)
            if self.stages.index((name, _)) < self._stage_index()
        )

        if self.stage == "processing":
            pct_match = re.search(r"(\d+)%", line)
            if pct_match:
                sub_progress = int(pct_match.group(1))
            else:
                chunk_match = re.search(r"chunk\s*(\d+)\s*/\s*(\d+)", line, re.IGNORECASE)
                if chunk_match:
                    sub_progress = int(int(chunk_match.group(1)) / int(chunk_match.group(2)) * 100)
                else:
                    sub_progress = 50
            return min(base + int(sub_progress * self.stage_weights[2] / 100), 99)
        elif self.stage == "saving":
            return base
        elif self.stage == "done":
            return 100

        return min(base + 1, 99)

    def _stage_index(self):
        for i, (name, _) in enumerate(self.stages):
            if name == self.stage:
                return i
        return 0
