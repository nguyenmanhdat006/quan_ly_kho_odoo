/**
 *------------------------------------------------------------------------------
 * Odoo Web Boostrap Code
 *------------------------------------------------------------------------------
 */
(function () {
    "use strict";

    class ModuleLoader {
        /** @type {Map<string,{fn: Function, deps: string[]}>} mapping name => deps/fn */
        factories = new Map();
        /** @type {Set<string>} names of modules waiting to be started */
        jobs = new Set();
        /** @type {Set<string>} names of failed modules */
        failed = new Set();

        /** @type {Map<string,any>} mapping name => value */
        modules = new Map();

        bus = new EventTarget();

        checkErrorProm = null;

        /**
         * @param {string} name
         * @param {string[]} deps
         * @param {Function} factory
         */
        define(name, deps, factory) {
            if (typeof name !== "string") {
                throw new Error(`Invalid name definition: ${name} (should be a string)"`);
            }
            if (!(deps instanceof Array)) {
                throw new Error(`Dependencies should be defined by an array: ${deps}`);
            }
            if (typeof factory !== "function") {
                throw new Error(`Factory should be defined by a function ${factory}`);
            }
            if (!this.factories.has(name)) {
                this.factories.set(name, {
                    deps,
                    fn: factory,
                    ignoreMissingDeps: globalThis.__odooIgnoreMissingDependencies,
                });
                this.addJob(name);
                this.checkErrorProm ||= Promise.resolve().then(() => {
                    this.checkAndReportErrors();
                    this.checkErrorProm = null;
                });
            }
        }

        addJob(name) {
            this.jobs.add(name);
            this.startModules();
        }

        findJob() {
            for (const job of this.jobs) {
                if (this.factories.get(job).deps.every((dep) => this.modules.has(dep))) {
                    return job;
                }
            }
            return null;
        }

        startModules() {
            let job;
            while ((job = this.findJob())) {
                this.startModule(job);
            }
        }

        startModule(name) {
            const require = (name) => this.modules.get(name);
            this.jobs.delete(name);
            const factory = this.factories.get(name);
            let value = null;
            try {
                value = factory.fn(require);
            } catch (error) {
                this.failed.add(name);
                throw new Error(`Error while loading "${name}":\n${error}`);
            }
            this.modules.set(name, value);
            this.bus.dispatchEvent(
                new CustomEvent("module-started", { detail: { moduleName: name, module: value } })
            );
        }

        findErrors() {
            // cycle detection
            const dependencyGraph = new Map();
            for (const job of this.jobs) {
                dependencyGraph.set(job, this.factories.get(job).deps);
            }
            function visitJobs(jobs, visited = new Set()) {
                for (const job of jobs) {
                    const result = visitJob(job, visited);
                    if (result) {
                        return result;
                    }
                }
                return null;
            }

            function visitJob(job, visited) {
                if (visited.has(job)) {
                    const jobs = Array.from(visited).concat([job]);
                    const index = jobs.indexOf(job);
                    return jobs
                        .slice(index)
                        .map((j) => `"${j}"`)
                        .join(" => ");
                }
                const deps = dependencyGraph.get(job);
                return deps ? visitJobs(deps, new Set(visited).add(job)) : null;
            }

            // missing dependencies
            const missing = new Set();
            for (const job of this.jobs) {
                const factory = this.factories.get(job);
                if (factory.ignoreMissingDeps) {
                    continue;
                }
                for (const dep of factory.deps) {
                    if (!this.factories.has(dep)) {
                        missing.add(dep);
                    }
                }
            }

            return {
                failed: [...this.failed],
                cycle: visitJobs(this.jobs),
                missing: [...missing],
                unloaded: [...this.jobs].filter((j) => !this.factories.get(j).ignoreMissingDeps),
            };
        }

        async checkAndReportErrors() {
            const { failed, cycle, missing, unloaded } = this.findErrors();
            if (!failed.length && !unloaded.length) {
                return;
            }
            const debug = new URLSearchParams(location.search).get("debug");
            if (debug && debug !== "0") {
                const style = document.createElement("style");
                style.textContent = `
                    body::before {
                        font-weight: bold;
                        content: "An error occurred while loading javascript modules, you may find more information in the devtools console";
                        position: fixed;
                        left: 0;
                        bottom: 0;
                        z-index: 100000000000;
                        background-color: #C00;
                        color: #DDD;
                    }
                `;
                document.head.appendChild(style);
            }

            if (failed.length) {
                console.error("The following modules failed to load because of an error:", failed);
            }
            if (missing) {
                console.error(
                    "The following modules are needed by other modules but have not been defined, they may not be present in the correct asset bundle:",
                    missing
                );
            }
            if (cycle) {
                console.error(
                    "The following modules could not be loaded because they form a dependency cycle:",
                    cycle
                );
            }
            if (unloaded) {
                console.error(
                    "The following modules could not be loaded because they have unmet dependencies, this is a secondary error which is likely caused by one of the above problems:",
                    unloaded
                );
            }
        }
    }

    if (!globalThis.odoo) {
        globalThis.odoo = {};
    }
    const odoo = globalThis.odoo;
    if (odoo.debug && !new URLSearchParams(location.search).has("debug")) {
        // remove debug mode if not explicitely set in url
        odoo.debug = "";
    }

    const loader = new ModuleLoader();
    odoo.define = loader.define.bind(loader);

    odoo.loader = loader;
})();
