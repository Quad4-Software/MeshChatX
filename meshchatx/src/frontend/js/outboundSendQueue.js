/**
 * Serial outbound job queue: one job runs at a time so later messages reuse
 * the route established while sending earlier ones to the same peer.
 */
function jobMatches(job, match) {
    if (!job || !match) {
        return false;
    }
    if (match.pendingHash && job.pendingHash === match.pendingHash) {
        return true;
    }
    if (match.messageHash && job.messageHash === match.messageHash) {
        return true;
    }
    if (match.cancelKey && job.cancelKey === match.cancelKey) {
        return true;
    }
    return false;
}

export function createOutboundQueue(processJob) {
    const queue = [];
    let running = false;
    let currentJob = null;

    async function run() {
        if (running) {
            return;
        }
        running = true;
        try {
            while (queue.length) {
                const job = queue.shift();
                if (job?.cancelled || job?.dropped) {
                    continue;
                }
                currentJob = job;
                try {
                    await processJob(job);
                } finally {
                    if (currentJob === job) {
                        currentJob = null;
                    }
                }
            }
        } finally {
            running = false;
            currentJob = null;
        }
    }

    function clear() {
        // Dropped (teardown) is weaker than user-cancelled: an in-flight job
        // whose REST send already reached the backend must not be cancelled
        // server-side when the view goes away.
        for (const job of queue) {
            job.dropped = true;
        }
        queue.length = 0;
        if (currentJob) {
            currentJob.dropped = true;
        }
    }

    return {
        enqueue(job) {
            queue.push(job);
            void run();
        },
        cancelJob(match) {
            if (currentJob && jobMatches(currentJob, match)) {
                currentJob.cancelled = true;
            }
            for (const job of queue) {
                if (jobMatches(job, match)) {
                    job.cancelled = true;
                }
            }
        },
        clear,
        get length() {
            return queue.length;
        },
        get isRunning() {
            return running;
        },
    };
}
