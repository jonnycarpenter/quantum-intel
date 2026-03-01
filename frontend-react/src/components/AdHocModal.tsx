import { X, Download, FileText } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useEffect } from 'react'

interface Props {
    isOpen: boolean
    onClose: () => void
    content: string
    title?: string
}

export default function AdHocModal({ isOpen, onClose, content, title = "Ad-Hoc Analysis" }: Props) {

    // Prevent body scroll when open
    useEffect(() => {
        if (isOpen) {
            document.body.style.overflow = 'hidden'
        } else {
            document.body.style.overflow = ''
        }
    }, [isOpen])

    if (!isOpen) return null

    const handleDownloadMarkdown = () => {
        const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${title.toLowerCase().replace(/\s+/g, '_')}.md`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
    }

    const handleDownloadPDF = () => {
        // A simple native print triggers the PDF dialog in most modern browsers.
        // CSS print media queries will hide the rest of the app shell (App.tsx needs print:hidden on navigation).
        window.print()
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm print:bg-white print:backdrop-blur-none" onClick={onClose}>
            {/* Modal Container */}
            <div
                className="relative w-full max-w-5xl max-h-[90vh] flex flex-col bg-bg-primary border border-border rounded-xl shadow-2xl print:max-h-none print:shadow-none print:border-none print:w-full"
                onClick={e => e.stopPropagation()} // Prevent clicks inside from closing
            >

                {/* Header - hide on print */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-bg-secondary print:hidden rounded-t-xl">
                    <div className="flex items-center gap-3">
                        <h2 className="text-lg font-semibold text-text-primary">{title}</h2>
                        <span className="px-2 py-0.5 text-xs font-medium bg-accent-purple/20 text-accent-purple rounded shadow-[0_0_10px_rgba(168,85,247,0.3)]">
                            Nano Banana 2 Generation
                        </span>
                    </div>

                    <div className="flex items-center gap-3">
                        <button
                            onClick={handleDownloadPDF}
                            className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-text-secondary bg-bg-tertiary hover:bg-bg-hover rounded-md transition-colors"
                            title="Download as PDF"
                        >
                            <FileText className="w-4 h-4" />
                            PDF
                        </button>
                        <button
                            onClick={handleDownloadMarkdown}
                            className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-text-secondary bg-bg-tertiary hover:bg-bg-hover rounded-md transition-colors"
                            title="Download Raw Markdown"
                        >
                            <Download className="w-4 h-4" />
                            Markdown
                        </button>
                        <div className="w-px h-5 bg-border mx-1" />
                        <button
                            onClick={onClose}
                            className="p-1.5 text-text-muted hover:text-text-primary hover:bg-bg-hover rounded-md transition-colors"
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>
                </div>

                {/* Content Area */}
                <div className="flex-1 overflow-y-auto px-8 py-6 prose prose-invert prose-teal max-w-none print:p-0 print:overflow-visible text-text-primary">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
                        // Custom renderers to fit the Ket Zero theme
                        h1: ({ node, ...props }) => <h1 className="text-2xl font-bold text-text-primary mt-6 mb-4 border-b border-border pb-2" {...props} />,
                        h2: ({ node, ...props }) => <h2 className="text-xl font-semibold text-text-primary mt-6 mb-3" {...props} />,
                        h3: ({ node, ...props }) => <h3 className="text-lg font-medium text-text-secondary mt-5 mb-2" {...props} />,
                        p: ({ node, ...props }) => <p className="text-text-secondary leading-relaxed mb-4" {...props} />,
                        ul: ({ node, ...props }) => <ul className="list-disc pl-6 text-text-secondary space-y-1 mb-4" {...props} />,
                        ol: ({ node, ...props }) => <ol className="list-decimal pl-6 text-text-secondary space-y-1 mb-4" {...props} />,
                        a: ({ node, ...props }) => <a className="text-accent-teal hover:underline" {...props} />,
                        strong: ({ node, ...props }) => <strong className="font-semibold text-text-primary" {...props} />,
                        img: ({ node, ...props }) => (
                            <div className="my-6">
                                <img className="max-w-full rounded-lg border border-border shadow-lg" {...props} />
                            </div>
                        ),
                        table: ({ node, ...props }) => (
                            <div className="overflow-x-auto my-6">
                                <table className="min-w-full divide-y divide-border border border-border rounded-lg" {...props} />
                            </div>
                        ),
                        th: ({ node, ...props }) => <th className="px-4 py-3 bg-bg-secondary text-left text-sm font-semibold text-text-primary" {...props} />,
                        td: ({ node, ...props }) => <td className="px-4 py-3 bg-bg-primary text-sm text-text-secondary border-t border-border" {...props} />
                    }}>
                        {content}
                    </ReactMarkdown>
                </div>
            </div>
        </div>
    )
}
