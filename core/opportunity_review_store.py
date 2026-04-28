from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models.opportunity_review_view import OpportunityReviewView
from shared.errors import NotFoundError, StorageError


class OpportunityReviewStore:
    def __init__(
        self,
        reviews_path: str = "data/opportunity_reviews.json",
    ) -> None:
        self.reviews_path = Path(reviews_path)
        self.reviews_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.reviews_path.exists():
            self._write_raw({"reviews": {}})

    def create_review_view(self, review_view: OpportunityReviewView) -> OpportunityReviewView:
        data = self._read_raw()
        reviews = data["reviews"]

        for existing in reviews.values():
            existing_review = OpportunityReviewView.from_dict(existing)
            if existing_review.opportunity_id == review_view.opportunity_id:
                return existing_review

        if review_view.review_view_id in reviews:
            raise StorageError(f"Opportunity review already exists: {review_view.review_view_id}")

        reviews[review_view.review_view_id] = review_view.to_dict()
        self._write_raw(data)
        return review_view

    def update_review_view(self, review_view: OpportunityReviewView) -> OpportunityReviewView:
        data = self._read_raw()
        reviews = data["reviews"]

        if review_view.review_view_id not in reviews:
            raise NotFoundError(f"Opportunity review not found: {review_view.review_view_id}")

        review_view.touch()
        reviews[review_view.review_view_id] = review_view.to_dict()
        self._write_raw(data)
        return review_view

    def get_review_view(self, review_view_id: str) -> OpportunityReviewView:
        data = self._read_raw()
        reviews = data["reviews"]

        if review_view_id not in reviews:
            raise NotFoundError(f"Opportunity review not found: {review_view_id}")

        return OpportunityReviewView.from_dict(reviews[review_view_id])

    def get_by_opportunity_id(self, opportunity_id: str) -> OpportunityReviewView:
        data = self._read_raw()
        reviews = data["reviews"]

        for item in reviews.values():
            review = OpportunityReviewView.from_dict(item)
            if review.opportunity_id == opportunity_id:
                return review

        raise NotFoundError(f"Opportunity review not found for opportunity_id: {opportunity_id}")

    def list_review_views(self) -> list[OpportunityReviewView]:
        data = self._read_raw()
        return [OpportunityReviewView.from_dict(item) for item in data["reviews"].values()]

    def _read_raw(self) -> dict[str, Any]:
        try:
            with self.reviews_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            raise StorageError(f"Could not read opportunity review store: {exc}") from exc

    def _write_raw(self, data: dict[str, Any]) -> None:
        try:
            with self.reviews_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            raise StorageError(f"Could not write opportunity review store: {exc}") from exc