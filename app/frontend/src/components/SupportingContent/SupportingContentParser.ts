type ParsedSupportingContentItem = {
    title: string;
    content: string;
};

export function parseSupportingContentItem(item: string): ParsedSupportingContentItem {
    // Assumes the item has the format ###url### content
    const match = item.match(/###(.*?)###\s*(.*)/);
    if (match && match[1] && match[2]) {
        return {
            title: match[1],
            content: match[2]
        };
    };

    return {
        title: "",
        content: ""
    };

    // Assumes the item starts with the file name followed by : and the content.
    // Example: "sdp_corporate.pdf: this is the content that follows".
    const parts = item.split(": ");
    const title = parts[0];
    const content = parts.slice(1).join(": ");

    return {
        title,
        content
    };
}
