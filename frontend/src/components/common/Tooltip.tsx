"use client";

import React, { useState, useRef, useEffect, ReactElement, ReactNode, cloneElement } from "react";

interface TooltipProps {
  children: ReactElement;
  content: ReactNode;
  position?: "top" | "bottom" | "left" | "right";
  delay?: number;
}

export function Tooltip({
  children,
  content,
  position = "top",
  delay = 200,
}: TooltipProps) {
  const [isVisible, setIsVisible] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  const showTooltip = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => setIsVisible(true), delay);
  };

  const hideTooltip = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setIsVisible(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      hideTooltip();
    }
  };

  // Position tooltip
  useEffect(() => {
    if (!isVisible || !wrapperRef.current || !tooltipRef.current) return;

    const trigger = wrapperRef.current.getBoundingClientRect();
    const tooltip = tooltipRef.current.getBoundingClientRect();
    const viewport = {
      width: window.innerWidth,
      height: window.innerHeight,
    };

    let top = 0;
    let left = 0;

    switch (position) {
      case "top":
        top = trigger.top - tooltip.height - 8;
        left = trigger.left + (trigger.width - tooltip.width) / 2;
        break;
      case "bottom":
        top = trigger.bottom + 8;
        left = trigger.left + (trigger.width - tooltip.width) / 2;
        break;
      case "left":
        top = trigger.top + (trigger.height - tooltip.height) / 2;
        left = trigger.left - tooltip.width - 8;
        break;
      case "right":
        top = trigger.top + (trigger.height - tooltip.height) / 2;
        left = trigger.right + 8;
        break;
    }

    // Keep in viewport
    left = Math.max(8, Math.min(left, viewport.width - tooltip.width - 8));
    top = Math.max(8, Math.min(top, viewport.height - tooltip.height - 8));

    tooltipRef.current.style.top = `${top}px`;
    tooltipRef.current.style.left = `${left}px`;
  }, [isVisible, position]);

  // Wrap child in a span to attach events
  const child = React.Children.only(children);
  const childProps = child.props as Record<string, unknown>;
  const wrappedChild = cloneElement(child as ReactElement<Record<string, unknown>>, {
    ...childProps,
    onMouseEnter: (e: React.MouseEvent) => {
      showTooltip();
      (childProps.onMouseEnter as ((e: React.MouseEvent) => void) | undefined)?.(e);
    },
    onMouseLeave: (e: React.MouseEvent) => {
      hideTooltip();
      (childProps.onMouseLeave as ((e: React.MouseEvent) => void) | undefined)?.(e);
    },
    onFocus: (e: React.FocusEvent) => {
      showTooltip();
      (childProps.onFocus as ((e: React.FocusEvent) => void) | undefined)?.(e);
    },
    onBlur: (e: React.FocusEvent) => {
      hideTooltip();
      (childProps.onBlur as ((e: React.FocusEvent) => void) | undefined)?.(e);
    },
    onKeyDown: (e: React.KeyboardEvent) => {
      handleKeyDown(e);
      (childProps.onKeyDown as ((e: React.KeyboardEvent) => void) | undefined)?.(e);
    },
    "aria-describedby": isVisible ? "tooltip-content" : undefined,
  });

  return (
    <>
      <span
        ref={wrapperRef}
        style={{ display: "inline-block" }}
        {...{
          onMouseEnter: showTooltip,
          onMouseLeave: hideTooltip,
          onFocus: showTooltip,
          onBlur: hideTooltip,
        }}
      >
        {wrappedChild}
      </span>
      {isVisible && (
        <div
          ref={tooltipRef}
          id="tooltip-content"
          role="tooltip"
          className="fixed z-50 rounded-ctl bg-night/95 px-3 py-2 text-sm text-text shadow-lg border border-border pointer-events-none animate-fade-in"
          style={{ opacity: isVisible ? 1 : 0, transition: "opacity 150ms" }}
        >
          {content}
        </div>
      )}
    </>
  );
}