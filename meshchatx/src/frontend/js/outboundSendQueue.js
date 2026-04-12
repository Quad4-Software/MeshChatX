/**
 * Serial outbound job queue: one job runs at a time so later messages reuse
 * the route established while sending earlier ones to the same peer.
 */
export function createOutboundQueue(processJob) {
    const queue = [];
    let running = false;

    async function run() {
        if (running) {
            return;
        }
        running = true;
        try {
            while (queue.length) {
                const job = queue.shift();
                await processJob(job);
            }
        } finally {
            running = false;
        }
    }

    return {
        enqueue(job) {
            queue.push(job);
            void run();
        },
        get length() {
            return queue.length;
        },
        get isRunning() {
            return running;
        },
    };
}
