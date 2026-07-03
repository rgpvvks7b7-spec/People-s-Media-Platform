import React, { useEffect, useRef, useState } from "react";

const PULL_THRESHOLD = 68;
const MAX_PULL = 112;

function canUsePullToRefresh() {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(pointer: coarse)").matches || "ontouchstart" in window;
}

export function PullToRefresh({ children, disabled = false, onRefresh }) {
  const [pullDistance, setPullDistance] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const enabled = canUsePullToRefresh();
  const startY = useRef(0);
  const startX = useRef(0);
  const tracking = useRef(false);
  const pulling = useRef(false);
  const pullDistanceRef = useRef(0);
  const refreshingRef = useRef(false);

  useEffect(() => {
    pullDistanceRef.current = pullDistance;
  }, [pullDistance]);

  useEffect(() => {
    refreshingRef.current = refreshing;
  }, [refreshing]);

  useEffect(() => {
    if (!enabled || disabled || !onRefresh) return undefined;

    function scrollTop() {
      return window.scrollY || document.documentElement.scrollTop || 0;
    }

    function resetPull() {
      tracking.current = false;
      pulling.current = false;
      if (!refreshingRef.current) setPullDistance(0);
    }

    async function runRefresh() {
      setRefreshing(true);
      setPullDistance(PULL_THRESHOLD);
      try {
        await onRefresh();
      } finally {
        setRefreshing(false);
        setPullDistance(0);
        tracking.current = false;
        pulling.current = false;
      }
    }

    function onTouchStart(event) {
      if (refreshingRef.current || scrollTop() > 2) return;
      if (event.touches.length !== 1) return;
      const target = event.target;
      if (target instanceof Element && target.closest(".modal-backdrop, .review-panel, .bottom-nav")) return;

      startY.current = event.touches[0].clientY;
      startX.current = event.touches[0].clientX;
      tracking.current = true;
      pulling.current = false;
    }

    function onTouchMove(event) {
      if (!tracking.current || refreshingRef.current) return;

      const touch = event.touches[0];
      const deltaY = touch.clientY - startY.current;
      const deltaX = touch.clientX - startX.current;

      if (!pulling.current) {
        if (Math.abs(deltaX) > Math.abs(deltaY)) {
          tracking.current = false;
          return;
        }
        if (deltaY <= 6 || scrollTop() > 2) return;
        pulling.current = true;
      }

      if (deltaY <= 0) {
        setPullDistance(0);
        return;
      }

      event.preventDefault();
      setPullDistance(Math.min(deltaY * 0.55, MAX_PULL));
    }

    function onTouchEnd() {
      if (!tracking.current) return;
      if (pulling.current && pullDistanceRef.current >= PULL_THRESHOLD) {
        runRefresh();
        return;
      }
      resetPull();
    }

    window.addEventListener("touchstart", onTouchStart, { passive: true });
    window.addEventListener("touchmove", onTouchMove, { passive: false });
    window.addEventListener("touchend", onTouchEnd, { passive: true });
    window.addEventListener("touchcancel", onTouchEnd, { passive: true });

    return () => {
      window.removeEventListener("touchstart", onTouchStart);
      window.removeEventListener("touchmove", onTouchMove);
      window.removeEventListener("touchend", onTouchEnd);
      window.removeEventListener("touchcancel", onTouchEnd);
    };
  }, [disabled, enabled, onRefresh]);

  if (!enabled || disabled || !onRefresh) {
    return children;
  }

  const ready = pullDistance >= PULL_THRESHOLD;
  const indicatorHeight = refreshing ? PULL_THRESHOLD : pullDistance;
  const label = refreshing
    ? "Refreshing…"
    : ready
      ? "Release to refresh"
      : "Pull to refresh";

  return (
    <div className={`pull-refresh${refreshing ? " pull-refresh--active" : ""}`}>
      <div
        className={`pull-refresh-indicator${ready || refreshing ? " pull-refresh-indicator--ready" : ""}`}
        style={{ height: `${indicatorHeight}px` }}
        aria-live="polite"
        aria-hidden={indicatorHeight <= 0 && !refreshing}
      >
        <span className={`pull-refresh-spinner${refreshing ? " pull-refresh-spinner--spin" : ""}`} aria-hidden="true" />
        <span className="pull-refresh-label">{label}</span>
      </div>
      <div
        className="pull-refresh-body"
        style={{ transform: indicatorHeight ? `translateY(${indicatorHeight}px)` : undefined }}
      >
        {children}
      </div>
    </div>
  );
}
