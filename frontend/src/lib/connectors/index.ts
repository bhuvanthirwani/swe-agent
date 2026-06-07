// ============================================================
// Connectors — Integration Framework for External Services
// Competitor Feature: CrewAI/n8n/Composio-style connectors
// Supports Slack, GitHub webhooks, Email, and custom webhooks.
// ============================================================

export type ConnectorType = 'slack' | 'github' | 'email' | 'webhook' | 'discord';
export type TriggerType = 'manual' | 'webhook' | 'schedule' | 'event';

export interface Connector {
  id: string;
  type: ConnectorType;
  name: string;
  description: string;
  icon: string;
  enabled: boolean;
  config: Record<string, string>;
  events: ConnectorEvent[];
}

export interface ConnectorEvent {
  id: string;
  connectorId: string;
  action: string;
  timestamp: number;
  success: boolean;
  message?: string;
}

export interface WebhookTrigger {
  id: string;
  name: string;
  url: string;
  method: 'POST' | 'GET';
  headers?: Record<string, string>;
  payloadTemplate?: string;
  enabled: boolean;
  lastTriggered?: number;
  triggerCount: number;
}

export interface PipelineTrigger {
  id: string;
  name: string;
  type: TriggerType;
  config: {
    // Webhook config
    webhookSecret?: string;
    // Schedule config (cron)
    cronExpression?: string;
    // Event config
    eventSource?: string;
    eventType?: string;
  };
  pipelineConfig: {
    requirement?: string;          // Fixed requirement template
    requirementTemplate?: string;  // Template with {{variables}}
    flowName?: string;
    hitlEnabled?: boolean;
  };
  enabled: boolean;
  createdAt: number;
}

// ─── Built-in Connector definitions ─────────────────────────

export async function fetchConnectors(): Promise<Connector[]> {
  try {
    const res = await fetch('/api/connectors');
    if (!res.ok) throw new Error('Failed to fetch connectors');
    return await res.json();
  } catch (error) {
    console.error(error);
    return [];
  }
}

// ─── Connector Actions ───────────────────────────────────────

interface NotificationPayload {
  title: string;
  message: string;
  status: 'success' | 'error' | 'info';
  metadata?: Record<string, unknown>;
}

/**
 * Send a Slack notification via incoming webhook.
 */
export async function sendSlackNotification(
  webhookUrl: string,
  payload: NotificationPayload
): Promise<boolean> {
  try {
    const statusEmoji = payload.status === 'success' ? '✅' : payload.status === 'error' ? '❌' : 'ℹ️';
    const res = await fetch(webhookUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: `${statusEmoji} *${payload.title}*\n${payload.message}`,
        blocks: [
          {
            type: 'section',
            text: {
              type: 'mrkdwn',
              text: `${statusEmoji} *${payload.title}*\n${payload.message}`,
            },
          },
        ],
      }),
    });
    return res.ok;
  } catch {
    return false;
  }
}

/**
 * Send a Discord notification via webhook.
 */
export async function sendDiscordNotification(
  webhookUrl: string,
  payload: NotificationPayload
): Promise<boolean> {
  try {
    const statusEmoji = payload.status === 'success' ? '✅' : payload.status === 'error' ? '❌' : 'ℹ️';
    const res = await fetch(webhookUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        content: `${statusEmoji} **${payload.title}**\n${payload.message}`,
        embeds: [{
          title: payload.title,
          description: payload.message,
          color: payload.status === 'success' ? 0x10b981 : payload.status === 'error' ? 0xef4444 : 0x6366f1,
        }],
      }),
    });
    return res.ok;
  } catch {
    return false;
  }
}

/**
 * Send a generic webhook notification.
 */
export async function sendWebhookNotification(
  url: string,
  payload: NotificationPayload,
  headers?: Record<string, string>
): Promise<boolean> {
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...headers },
      body: JSON.stringify({
        event: 'pipeline_notification',
        timestamp: new Date().toISOString(),
        ...payload,
      }),
    });
    return res.ok;
  } catch {
    return false;
  }
}

/**
 * Dispatch a notification across all enabled connectors.
 */
export async function dispatchNotification(
  connectors: Connector[],
  payload: NotificationPayload
): Promise<Record<string, boolean>> {
  const results: Record<string, boolean> = {};

  for (const conn of connectors.filter(c => c.enabled)) {
    switch (conn.type) {
      case 'slack':
        if (conn.config.webhookUrl) {
          results[conn.id] = await sendSlackNotification(conn.config.webhookUrl, payload);
        }
        break;
      case 'discord':
        if (conn.config.webhookUrl) {
          results[conn.id] = await sendDiscordNotification(conn.config.webhookUrl, payload);
        }
        break;
      case 'webhook':
        if (conn.config.url) {
          results[conn.id] = await sendWebhookNotification(conn.config.url, payload);
        }
        break;
      case 'email':
        // Email would require SMTP setup — placeholder
        results[conn.id] = false;
        break;
      default:
        break;
    }
  }

  return results;
}
