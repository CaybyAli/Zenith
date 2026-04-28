from pathlib import Path
import shutil


class FacelessAssembler:
    def assemble(self, asset_pack) -> str:
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        output_path = output_dir / f"{asset_pack.job_id}_faceless_final.mp4"

        candidates = [
            Path("sample.mp4"),
        ]

        source = None
        for candidate in candidates:
            if candidate.exists():
                source = candidate
                break

        if source is None:
            raise FileNotFoundError(
                "No fallback video found for faceless MVP assembly"
            )

        shutil.copy(source, output_path)

        print(f"[FacelessAssembler] Rendering faceless video for {asset_pack.job_id}...")

        return str(output_path)