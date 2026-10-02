/**
 * Analysis types shown in the UI, mapped onto the backend `preset` values.
 * Wording follows the UI spec: "What should exist?" vs "What currently exists?".
 */
export const ANALYSIS_TYPES = {
  spec_coverage: {
    label: 'Compare requirements',
    short: 'Requirements',
    blurb: 'Find gaps between a specification and the documentation that describes the current state.',
    reference: {
      title: 'What should exist?',
      text: 'The documents that define the expected requirements, standards or target state.',
      examples: 'SRS · BRD · Requirements · Standards · Policies',
    },
    existing: {
      title: 'What currently exists?',
      text: 'The documents that describe the current state.',
      examples: 'SDD · API documentation · Existing project docs',
    },
  },
  resume_jd: {
    label: 'Resume vs Job Description',
    short: 'Resume vs JD',
    blurb: 'Find which job requirements a resume supports, and which are missing or weak.',
    reference: {
      title: 'What should exist?',
      text: 'The job description that lists the required skills and experience.',
      examples: 'Job description · Role requirements',
    },
    existing: {
      title: 'What currently exists?',
      text: 'The resume (or profile) to check against those requirements.',
      examples: 'Resume · CV · Portfolio summary',
    },
  },
}

export const analysisType = (preset) => ANALYSIS_TYPES[preset] || ANALYSIS_TYPES.spec_coverage
