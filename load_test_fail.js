import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
    vus: 20,
    duration: '30s',
    thresholds: {
        http_req_failed: ['rate<0.01'],
        http_req_duration: ['p(95)<1'],
    },
};

export default function loadTest() {
    const response = http.get('http://127.0.0.1:8000/tasks');

    check(response, {
        'status is 200': (r) => r.status === 200,
    });

    sleep(1);
}
