import http from 'k6/http';
import { check, sleep } from 'k6';

// K6 Load Test Configuration for SSE Endpoint
// Target: 50 concurrent active streams, p95 latency under 500ms, error rate < 1%
export const options = {
  stages: [
    { duration: '10s', target: 20 }, // Ramp up to 20 concurrent stream users
    { duration: '25s', target: 50 }, // Sustained load of 50 active streams
    { duration: '5s', target: 0 },   // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests must complete under 500ms
    http_req_failed: ['rate<0.01'],    // Error rate strictly under 1%
  },
};

export default function () {
  const targetUrl = __ENV.TARGET_URL || 'http://localhost:8000/api/v1/stream/run_load_test';
  const params = {
    headers: {
      'Accept': 'text/event-stream',
      'Authorization': 'Bearer mock_jwt_load_test_token',
    },
    timeout: '10s',
  };

  const res = http.get(targetUrl, params);

  check(res, {
    'status is 200': (r) => r.status === 200,
    'content type is event-stream': (r) =>
      r.headers['Content-Type'] && r.headers['Content-Type'].includes('text/event-stream'),
  });

  sleep(0.5);
}
