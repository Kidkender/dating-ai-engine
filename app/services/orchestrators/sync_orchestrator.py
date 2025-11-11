"""
Sync Orchestrator - Điều phối toàn bộ sync flow
Responsibility: Coordinate sync process, không chứa business logic
"""

import logging
import time
from datetime import datetime

from app.schemas.sync import DatingAppUser, SyncRequest, SyncSummary, UserSyncResult
from app.services.user_sync_service import UserSyncService
from app.services.dating_app_client import DatingAppClient

logger = logging.getLogger(__name__)


class SyncOrchestrator:
    """Orchestrates the sync process between dating app and AI engine"""

    def __init__(
        self,
        dating_app_client: DatingAppClient,
        user_sync_service: UserSyncService,
    ):
        self.dating_app_client = dating_app_client
        self.user_sync_service = user_sync_service

    async def sync_users_from_dating_app(
        self, sync_request: SyncRequest
    ) -> SyncSummary:
        """
        Main orchestration method for syncing users

        Args:
            sync_request: Sync configuration

        Returns:
            SyncSummary with aggregated results
        """
        start_time = time.time()
        summary = SyncSummary(sync_timestamp=datetime.now())

        try:
            # Step 1: Verify connection
            if not await self._verify_connection():
                summary.errors.append(
                    {
                        "error": "Failed to connect to dating app API",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                return summary

            # Step 2: Fetch users
            dating_app_users = await self.dating_app_client.fetch_all_users(
                limit=sync_request.limit
            )
            summary.total_users_pulled = len(dating_app_users)
            logger.info(f"Fetched {len(dating_app_users)} users from dating app")

            # Step 3: Process users
            user_results = await self._process_users(
                dating_app_users, sync_request, summary
            )

            # Step 4: Calculate statistics
            self._calculate_statistics(summary, user_results, start_time)

            logger.info(
                f"Sync completed: {summary.users_synced}/{summary.total_users_pulled} users synced"
            )
            return summary

        except Exception as e:
            logger.error(f"Error during sync orchestration: {e}", exc_info=True)
            summary.errors.append(
                {
                    "error": f"Sync failed: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                }
            )
            summary.total_duration_seconds = time.time() - start_time
            return summary

    async def _verify_connection(self) -> bool:
        """Verify connection to dating app"""
        return await self.dating_app_client.verify_connection()

    async def _process_users(
        self,
        dating_app_users: list[DatingAppUser],
        sync_request: SyncRequest,
        summary: SyncSummary,
    ) -> list[UserSyncResult]:
        """Process all users and update summary"""
        user_results = []

        for dating_user in dating_app_users:
            try:
                result = await self.user_sync_service.sync_single_user(
                    dating_user,
                    sync_request.force_resync,
                    sync_request.min_face_confidence,
                )
                user_results.append(result)

                self._update_summary(summary, result)

            except Exception as e:
                logger.error(
                    f"Error syncing user {dating_user.email}: {e}",
                    exc_info=True,
                    extra={"user_email": dating_user.email},
                )
                summary.users_skipped += 1
                summary.errors.append(
                    {
                        "email": dating_user.email,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        return user_results

    def _update_summary(self, summary: SyncSummary, result: UserSyncResult):
        """Update summary with single user result"""
        if result.success:
            summary.users_synced += 1
            summary.total_images_processed += result.images_processed
            summary.faces_detected += result.images_with_faces

            if result.is_active:
                summary.users_with_valid_faces += 1
            else:
                summary.users_without_faces += 1
        else:
            summary.users_skipped += 1
            summary.errors.append(
                {
                    "email": result.email,
                    "error": result.error_message,
                    "timestamp": datetime.now().isoformat(),
                }
            )

    def _calculate_statistics(
        self,
        summary: SyncSummary,
        user_results: list[UserSyncResult],
        start_time: float,
    ):
        """Calculate final statistics"""
        summary.faces_failed = summary.total_images_processed - summary.faces_detected

        if summary.faces_detected > 0:
            total_confidence = sum(
                img_result.face_confidence or 0
                for user_result in user_results
                for img_result in user_result.image_results
                if img_result.face_confidence is not None
            )
            summary.avg_confidence = total_confidence / summary.faces_detected

        summary.total_duration_seconds = time.time() - start_time
